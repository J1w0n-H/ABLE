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

def get_llm_response(model: str, messages, temperature = 0.0, n = 1, max_tokens = 1024):
    """Get response from LLM with retry logic"""
    max_retry = 5
    count = 0
    
    # Check API key
    import os
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY environment variable is not set!")
        print("   Please set it with: export OPENAI_API_KEY='your-api-key'")
        return None, None
    
    while count < max_retry:
        try:
            client = openai.OpenAI()
            print(f"  Attempt {count + 1}/{max_retry}: Sending request to {model}...")
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                n=n,
                max_tokens=max_tokens,
                timeout=30  # 30 second timeout
            )
            
            print(f"  ✓ Success! Received response.")
            return response.choices[0].message.content, response.usage
            
        except openai.APIError as e:
            print(f"  ❌ API Error: {e}")
            count += 1
            if count < max_retry:
                print(f"  Retrying in 3 seconds...")
                time.sleep(3)
                
        except openai.AuthenticationError as e:
            print(f"  ❌ Authentication Error: {e}")
            print(f"  Please check your OPENAI_API_KEY")
            return None, None
            
        except openai.RateLimitError as e:
            print(f"  ❌ Rate Limit Error: {e}")
            count += 1
            if count < max_retry:
                wait_time = 10 * count
                print(f"  Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                
        except Exception as e:
            print(f"  ❌ Unexpected Error: {type(e).__name__}: {e}")
            count += 1
            if count < max_retry:
                print(f"  Retrying in 3 seconds...")
                time.sleep(3)
    
    print(f"  ❌ Failed after {max_retry} attempts")
    return None, None
