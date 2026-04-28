import json
import os
import re
import threading
import datetime
import math
import logging
from openai import OpenAI

# Initialize MemPalace global configuration
# Disable ChromaDB telemetry to avoid missing modules (like posthog) in frozen builds
os.environ["ANONYMIZED_TELEMETRY"] = "False"
app_data_palace = os.path.join(os.environ.get("APPDATA", ""), "Suki8898", "MemPalace")
os.environ["MEMPALACE_PALACE_PATH"] = app_data_palace

class LLMManager:
    def __init__(self, settings_manager):
        self.settings = settings_manager
        self.history = []                                                          
        self.max_history = 20 
        app_data_dir = os.path.join(os.environ.get("APPDATA", ""), "Suki8898", "Suki Desktop Assistant")
        self.history_file = os.path.join(app_data_dir, "chat_history.json")
        self.load_history()

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = data.get("history", [])
            except:
                pass

    def save_history(self):
        max_hist = self.settings.get("history", "max_messages", default=20)
                                               
        if len(self.history) > max_hist:
            self.history = self.history[-max_hist:]
            
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump({
                "history": self.history
            }, f, ensure_ascii=False, indent=4)

    def generate_response(self, text, file_paths=None, callback=None):
        """Generates response asynchronously to avoid blocking UI"""
                                                                                    
        if text:
            self.history.append({"role": "user", "content": text})
        elif file_paths:
            self.history.append({"role": "user", "content": "[Đính kèm] " * len(file_paths)})
        
        self.save_history()

        def worker():
            try:
                response_text = self._call_api(text, file_paths=file_paths)
                self.history.append({"role": "assistant", "content": response_text})
                self.save_history()
                if callback:
                    callback(response_text, None)
            except Exception as e:
                import traceback
                traceback.print_exc()
                if callback:
                    callback(None, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _call_api(self, text, file_paths=None):
        provider = self.settings.get("ai", "provider")
        
        providers_dict = self.settings.get("ai", "providers")
        if providers_dict and provider in providers_dict:
            provider_cfg = providers_dict[provider]
            api_key = provider_cfg.get("api_key", "")
            model = provider_cfg.get("model", "")
            temp = provider_cfg.get("temperature", 0.7)
        else:
            api_key = self.settings.get("ai", "api_key", "")
            model = self.settings.get("ai", "model", "")
            temp = self.settings.get("ai", "temperature", 0.7)
            
        system_prompt = self.settings.get("ai", "system_prompt", "")
        
        char_name = self.settings.get("character", "current_character", default="Suki")
        if "{character_name}" in system_prompt:
            system_prompt = system_prompt.replace("{character_name}", char_name)
            
        emotions_list = self.settings.get("emotions", "list", default=["normal", "happy", "angry", "sad", "thinking", "suspicion", "surprised", "embarrassed", "annoyed", "confused", "dizzy", "smug", "hearthands", "sleepy", "hello"])
        emotions_str = ", ".join([f"<{e}>" for e in emotions_list])
        
        if not api_key:
            return "Vui lòng nhập API Key trong phần Cài đặt (Khay hệ thống -> Tùy chỉnh)."

                                                                    
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_sys_prompt = f"[Tình trạng thiết bị]\nThời gian hệ thống hiện tại: {current_time}\n\n" + system_prompt
        
                                                                    
        full_sys_prompt += f"\n\nCác thẻ biểu cảm bạn có thể dùng: {emotions_str}"

        static_knowledge = self.settings.get("general", "static_knowledge", default=[])
        # Backward compat: if old string format, wrap in list
        if isinstance(static_knowledge, str) and static_knowledge.strip():
            static_knowledge = [p.strip() for p in static_knowledge.split("\n\n") if p.strip()]
        if static_knowledge:
            top_n = self.settings.get("general", "knowledge_topn", default=3)
            full_text = "\n\n".join(static_knowledge)
            relevant_chunks = self._get_relevant_knowledge(text, full_text, static_knowledge, top_n)
            if relevant_chunks:
                sys_knowledge = "\n\n---\n".join(relevant_chunks)
                full_sys_prompt += f"\n\n[KIẾN THỨC NỀN TẢNG TIÊU CHUẨN MÀ BẠN PHẢI BIẾT VÀ TÌM ĐƯỢC LIÊN QUAN ĐẾN CÂU HỎI]:\n{sys_knowledge}"



        api_timeout = self.settings.get("ai", "api_timeout", default=30)
        
        if provider == "Google":
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=api_key, http_options={'timeout': float(api_timeout)})
                
                                                           
                gemini_history = []
                                                                                                     
                for msg in self.history[:-1]:
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append({"role": role, "parts": [{"text": msg["content"]}]})
                    
                
                                
                current_parts = []
                
                if file_paths:
                    import mimetypes
                    for path in file_paths:
                        if not os.path.exists(path):
                            continue
                            
                                                                           
                        ext = os.path.splitext(path)[1].lower()
                        if ext in ['.txt', '.csv', '.md', '.json']:
                            try:
                                with open(path, "r", encoding="utf-8") as f:
                                    doc_text = f.read()
                                if not text:
                                    text = ""
                                base_name = os.path.basename(path)
                                text += f"\n\n[Nội dung tệp đính kèm: {base_name}]\n{doc_text}\n"
                            except Exception as e:
                                text += f"\n\n[Lỗi đọc tệp đính kèm {base_name}: {e}]\n"
                        else:
                                           
                            with open(path, "rb") as f:
                                img_bytes = f.read()
                            mime_type, _ = mimetypes.guess_type(path)
                            if not mime_type:
                                mime_type = "image/jpeg"
                            image_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
                            current_parts.append(image_part)
                    
                contents = gemini_history
                                                                     
                if text and current_parts and current_parts[0].get("text"):
                    pass                   
                
                                                                   
                final_current_parts = []
                if text:
                    final_current_parts.append({"text": text})
                for part in current_parts:
                    final_current_parts.append(part)
                    
                if final_current_parts:
                    contents.append({"role": "user", "parts": final_current_parts})

                
                              
                logging.info("\n========= GOOGLE GEMINI REQUEST =========")
                logging.info(f"System Prompt:\n{full_sys_prompt}")
                logging.info(f"Query text:\n{text}")
                if file_paths:
                    logging.info(f"Attached files: {file_paths}")
                logging.info("=======================================")

                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=temp,
                        system_instruction=full_sys_prompt
                    )
                )
                
                logging.info("\n========= GOOGLE GEMINI RESPONSE ========")
                logging.info(response.text)
                logging.info("=======================================\n")
                
                return response.text
            except Exception as e:
                return f"Lỗi Google API: {e}"
            
        elif provider in ["OpenAI", "OpenRouter", "XAI", "NVIDIA", "LM Studio"]:
                                                       
            kwargs = {"api_key": api_key}
            if provider == "OpenRouter":
                kwargs["base_url"] = "https://openrouter.ai/api/v1"
            elif provider == "XAI":
                kwargs["base_url"] = "https://api.x.ai/v1"
            elif provider == "NVIDIA":
                kwargs["base_url"] = "https://integrate.api.nvidia.com/v1"
            elif provider == "LM Studio":
                port = provider_cfg.get("port", 1234) if providers_dict and provider in providers_dict else 1234
                kwargs["base_url"] = f"http://localhost:{port}/v1"
            
            client = OpenAI(**kwargs, timeout=float(api_timeout))
            messages = [{"role": "system", "content": full_sys_prompt}]
            
                                        
            for msg in self.history[:-1]:
                messages.append(msg)
                
                                        
            if file_paths:
                import base64
                import mimetypes
                
                content_array = []
                    
                for path in file_paths:
                    if not os.path.exists(path):
                        continue
                        
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ['.txt', '.csv', '.md', '.json']:
                        try:
                            with open(path, "r", encoding="utf-8") as file:
                                doc_text = file.read()
                            if not text:
                                text = ""
                            base_name = os.path.basename(path)
                            text += f"\n\n[Nội dung tệp đính kèm: {base_name}]\n{doc_text}\n"
                        except Exception as e:
                            text += f"\n\n[Lỗi đọc tệp đính kèm {base_name}: {e}]\n"
                    else:
                        with open(path, "rb") as image_file:
                            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                        mime_type, _ = mimetypes.guess_type(path)
                        if not mime_type:
                            mime_type = "image/jpeg"
                        
                        content_array.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        })
                
                if text:
                    content_array.insert(0, {"type": "text", "text": text})
                    
                messages.append({"role": "user", "content": content_array})
            else:
                if text:
                    messages.append({"role": "user", "content": text})
                
            logging.info(f"\n========= {provider.upper()} REQUEST =========")
                                                              
            log_messages = json.dumps(messages, ensure_ascii=False, indent=2)
            if file_paths:
                import re
                log_messages = re.sub(r'data:image/.*?;base64,.*?"', '"[BASE64_IMAGE_DATA]"', log_messages)
            logging.info(f"Messages Array:\n{log_messages}")
            logging.info("======================================")
                
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temp
            )
            
            resp_content = response.choices[0].message.content
            logging.info(f"\n========= {provider.upper()} RESPONSE ========")
            logging.info(resp_content)
            logging.info("=====================================\n")
            
            return resp_content
            
        return "Nhà cung cấp chưa được hỗ trợ hoàn chỉnh."

    def _get_relevant_knowledge(self, query, full_text, items=None, top_n=3):
        if not full_text.strip():
            return []
        
        # Use items list if available, otherwise fall back to full_text
        knowledge_items = items if items else [full_text]
            
        try:
            from mempalace.searcher import search_memories
            import os
            palace_path = os.path.join(os.environ.get("APPDATA", ""), "Suki8898", "Suki Desktop Assistant", "MemPalace")
            results = search_memories(query=query, palace_path=palace_path, wing="background", n_results=top_n)
            
            top_chunks = []
            if results and results.get("results"):
                for r in results["results"]:
                    chunk_text = r.get("text", "").strip()
                    if not chunk_text:
                        continue
                    # Deduplicate: skip if this chunk is largely contained in an existing one
                    is_duplicate = False
                    for existing in top_chunks:
                        # If >80% of the shorter text appears in the longer one, it's a duplicate
                        shorter, longer = (chunk_text, existing) if len(chunk_text) <= len(existing) else (existing, chunk_text)
                        if shorter[:200] in longer:
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        top_chunks.append(chunk_text)
                        
            logging.info(f"MemPalace Search for '{query}': Returned {len(top_chunks)} unique chunks.")
            if not top_chunks:
                # MemPalace has no data yet, use smart keyword fallback
                return self._keyword_fallback(query, knowledge_items, top_n=top_n)
            return top_chunks
        except Exception as e:
            logging.error(f"MemPalace Search error: {e}")
            # Fallback to keyword-scored items if MemPalace fails
            return self._keyword_fallback(query, knowledge_items, top_n=top_n)

    def _keyword_fallback(self, query, items, top_n=3, max_chars=2000):
        """Score knowledge items by keyword overlap with query, return top matches."""
        if not items:
            return []
        
        # Tokenize query into keywords (lowercase, remove punctuation)
        query_words = set(re.findall(r'\w+', query.lower()))
        # Remove very short/common words
        stop_words = {'là', 'và', 'của', 'có', 'không', 'được', 'cho', 'này', 'với', 'các',
                      'the', 'is', 'are', 'a', 'an', 'and', 'or', 'to', 'in', 'of', 'for',
                      'em', 'anh', 'tôi', 'bạn', 'gì', 'như', 'thế', 'nào', 'đã', 'sẽ', 'đang'}
        query_words = {w for w in query_words if len(w) > 1 and w not in stop_words}
        
        if not query_words:
            # No meaningful keywords, return first items up to max_chars
            result = []
            total = 0
            for item in items[:top_n]:
                if total + len(item) > max_chars:
                    break
                result.append(item)
                total += len(item)
            return result
        
        # Score each item by keyword hit count
        scored = []
        for i, item in enumerate(items):
            item_lower = item.lower()
            score = sum(1 for w in query_words if w in item_lower)
            scored.append((score, i, item))
        
        # Sort by score descending, then by original order for tie-breaking
        scored.sort(key=lambda x: (-x[0], x[1]))
        
        # Take top_n, respecting max_chars budget
        result = []
        total = 0
        for score, idx, item in scored[:top_n]:
            if total + len(item) > max_chars:
                remaining = max_chars - total
                if remaining > 50:
                    result.append(item[:remaining])
                break
            result.append(item)
            total += len(item)
        
        matched_scores = [s[0] for s in scored[:top_n]]
        logging.info(f"Keyword fallback for '{query}': {len(items)} items, "
                     f"returning top {len(result)} (scores: {matched_scores}).")
        return result
