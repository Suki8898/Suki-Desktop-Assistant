import json
import os
import threading
import datetime
import math
import logging
from openai import OpenAI

class LLMManager:
    def __init__(self, settings_manager):
        self.settings = settings_manager
        self.history = []                                                          
        self.max_history = 20 
        app_data_dir = os.path.join(os.environ.get("APPDATA", ""), "Suki8898", "Suki Desktop Assistant")
        self.history_file = os.path.join(app_data_dir, "chat_history.json")
        self.static_knowledge_cache = {"text": "", "chunks": [], "provider": ""}                                         
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
            
        emotions_list = self.settings.get("emotions", "list", default=["normal", "happy", "angry", "sad", "thinking", "suspicion", "surprised", "embarrassed", "annoyed", "confused", "dizzy", "smug"])
        emotions_str = ", ".join([f"<{e}>" for e in emotions_list])
        
        if not api_key:
            return "Vui lòng nhập API Key trong phần Cài đặt (Khay hệ thống -> Tùy chỉnh)."

                                                                    
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_sys_prompt = f"[Tình trạng thiết bị]\nThời gian hệ thống hiện tại: {current_time}\n\n" + system_prompt
        
                                                                    
        full_sys_prompt += f"\n\nCác thẻ biểu cảm bạn có thể dùng: {emotions_str}"

        static_knowledge = self.settings.get("general", "static_knowledge", default="")
        if static_knowledge:
            relevant_chunks = self._get_relevant_knowledge(text, static_knowledge)
            if relevant_chunks:
                sys_knowledge = "\n\n---\n".join(relevant_chunks)
                full_sys_prompt += f"\n\n[KIẾN THỨC NỀN TẢNG TIÊU CHUẨN MÀ BẠN PHẢI BIẾT VÀ TÌM ĐƯỢC LIÊN QUAN ĐẾN CÂU HỎI]:\n{sys_knowledge}"



        if provider == "Google":
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=api_key)
                
                                                           
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
            
        elif provider in ["OpenAI", "OpenRouter", "XAI"]:
                                                       
            kwargs = {"api_key": api_key}
            if provider == "OpenRouter":
                kwargs["base_url"] = "https://openrouter.ai/api/v1"
            elif provider == "XAI":
                kwargs["base_url"] = "https://api.x.ai/v1"
            
            client = OpenAI(**kwargs)
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

    def _cosine_similarity(self, vec1, vec2):
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def _get_embedding(self, text, provider, api_key):
        if not text.strip():
            return None
        
        try:
            logging.info(f"\n[EMBEDDING] Sending text to Embedding API ({provider}):\n{text}")
            if provider == "Google":
                from google import genai
                client = genai.Client(api_key=api_key)
                response = client.models.embed_content(
                    model='gemini-embedding-001',
                    contents=text,
                )
                if response.embeddings and len(response.embeddings) > 0:
                    return response.embeddings[0].values
            elif provider == "OpenAI":
                                                                                                                          
                                                                                                                       
                                                          
                kwargs = {"api_key": api_key}
                client = OpenAI(**kwargs)
                
                response = client.embeddings.create(
                    input=text,
                    model="text-embedding-3-small"                                  
                )
                return response.data[0].embedding
        except Exception as e:
            print(f"Embedding error: {e}")
        return None

    def _get_relevant_knowledge(self, query, full_text):
        if not full_text.strip():
            return []
            
        provider = self.settings.get("ai", "provider")
        
        if provider in ["OpenRouter", "XAI"]:
            return [full_text]
        providers_dict = self.settings.get("ai", "providers")
        api_key = ""
        if providers_dict and provider in providers_dict:
            api_key = providers_dict[provider].get("api_key", "")
        else:
            api_key = self.settings.get("ai", "api_key", "")
            
        if not api_key:
            return [full_text]           
            
                                                     
        if self.static_knowledge_cache.get("text") != full_text or self.static_knowledge_cache.get("provider") != provider:
                           
                                                                                       
            import re
            raw_chunks = [c.strip() for c in re.split(r'\n\s*\n', full_text) if c.strip()]
            
                                                                    
            final_chunks = []
            for rc in raw_chunks:
                if len(rc) > 500:
                    lines = rc.split('\n')
                                                
                    buf = ""
                    for l in lines:
                        if len(buf) + len(l) > 400 and buf:
                            final_chunks.append(buf.strip())
                            buf = l + "\n"
                        else:
                            buf += l + "\n"
                    if buf:
                        final_chunks.append(buf.strip())
                else:
                    final_chunks.append(rc)
            
            self.static_knowledge_cache["text"] = full_text
            self.static_knowledge_cache["provider"] = provider
            self.static_knowledge_cache["chunks"] = []
            
                              
            for c in final_chunks:
                emb = self._get_embedding(c, provider, api_key)
                if emb:
                    self.static_knowledge_cache["chunks"].append({
                        "text": c,
                        "vector": emb
                    })
                    
        if not self.static_knowledge_cache["chunks"]:
            return [full_text]                                                            
            
                     
        query_emb = self._get_embedding(query, provider, api_key)
        if not query_emb:
            return [full_text]                                
            
                        
        scored_chunks = []
        for chunk_data in self.static_knowledge_cache["chunks"]:
            score = self._cosine_similarity(query_emb, chunk_data["vector"])
            scored_chunks.append((score, chunk_data["text"]))
            
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        logging.info(f"RAG Similarity Scores for '{query}':")
        for s, c in scored_chunks[:3]:
            logging.info(f" - [{s:.4f}] {c[:50]}...")
        
                                                    
        top_chunks = [c for s, c in scored_chunks[:2] if s > 0.25]
            
        return top_chunks


