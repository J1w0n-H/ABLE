# Copyright (2025) Bytedance Ltd. and/or its affiliates

"""Configuration management for ABLE"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()

class Config:
    """ABLE Configuration"""
    
    # LLM Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    LLM_MODEL = os.getenv('ABLE_LLM_MODEL', 'gpt-4.1-mini')
    MAX_TOKENS = int(os.getenv('ABLE_MAX_TOKENS', '30000'))
    TEMPERATURE = float(os.getenv('ABLE_TEMPERATURE', '0.0'))
    LLM_RETRY = int(os.getenv('ABLE_LLM_RETRY', '5'))
    
    # Path Configuration
    OUTPUT_ROOT = os.getenv('REPO2RUN_OUTPUT_ROOT', './output')
    REPO_CACHE = os.getenv('ABLE_REPO_CACHE', './build_agent/utils/repo')
    
    # Build Configuration
    MAX_TURN = int(os.getenv('ABLE_MAX_TURN', '100'))
    TIMEOUT = int(os.getenv('ABLE_TIMEOUT', '14400'))
    DOCKER_IMAGE = os.getenv('ABLE_DOCKER_IMAGE', 'gcr.io/oss-fuzz-base/base-builder')
    MEMORY_LIMIT = os.getenv('ABLE_MEMORY_LIMIT', '30g')
    CPU_LIMIT = os.getenv('ABLE_CPU_LIMIT', '0-15')
    
    # Feature Flags
    USE_COMMAND_PATTERN = os.getenv('ABLE_USE_COMMAND_PATTERN', 'false').lower() == 'true'
    VERBOSE = os.getenv('ABLE_VERBOSE', 'false').lower() == 'true'
    DEBUG = os.getenv('ABLE_DEBUG', 'false').lower() == 'true'
    
    # Timeouts
    GIT_TIMEOUT = int(os.getenv('ABLE_GIT_TIMEOUT', '600'))
    DOCKER_BUILD_TIMEOUT = int(os.getenv('ABLE_DOCKER_BUILD_TIMEOUT', '600'))
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.OPENAI_API_KEY and 'gpt' in cls.LLM_MODEL.lower():
            errors.append("OPENAI_API_KEY is required for GPT models")
        
        if not cls.ANTHROPIC_API_KEY and 'claude' in cls.LLM_MODEL.lower():
            errors.append("ANTHROPIC_API_KEY is required for Claude models")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
    
    @classmethod
    def get_summary(cls):
        """Get configuration summary (safe for logging)"""
        return {
            'llm_model': cls.LLM_MODEL,
            'max_turn': cls.MAX_TURN,
            'timeout': cls.TIMEOUT,
            'docker_image': cls.DOCKER_IMAGE,
            'output_root': cls.OUTPUT_ROOT,
            'verbose': cls.VERBOSE,
            'debug': cls.DEBUG,
        }

