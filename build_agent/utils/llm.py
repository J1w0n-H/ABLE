# Copyright (2025) Bytedance Ltd. and/or its affiliates 

# Licensed under the Apache License, Version 2.0 (the "License"); 
# you may not use this file except in compliance with the License. 
# You may obtain a copy of the License at 

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software 
# distributed under the License is distributed on an "AS IS" BASIS, 
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
# See the License for the specific language governing permissions and 
# limitations under the License. 


import openai
import time
import os

# Support both direct execution and package import
try:
    from ..config import Config
    USE_CONFIG = True
except ImportError:
    try:
        from config import Config
        USE_CONFIG = True
    except ImportError:
        USE_CONFIG = False

def get_llm_response(model: str, messages, temperature = 0.0, n = 1, max_tokens = 1024):
    if USE_CONFIG:
        max_retry = Config.LLM_RETRY
        api_key = Config.OPENAI_API_KEY if 'gpt' in model.lower() else Config.ANTHROPIC_API_KEY
    else:
        max_retry = 5
        api_key = os.getenv('OPENAI_API_KEY', '')
    
    count = 0
    while count < max_retry:
        try:
            client = openai.OpenAI(api_key=api_key) if api_key else openai.OpenAI()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                n=n,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content, response.usage
        except Exception as e:
            print(f"LLM API Error: {e}")
            count += 1
            if count < max_retry:
                wait_time = 3 * (2 ** (count - 1))  # Exponential backoff
                print(f"Retrying in {wait_time} seconds... ({count}/{max_retry})")
                time.sleep(wait_time)
    
    print(f"Failed after {max_retry} retries")
    return None, None