# Copyright (2025) Bytedance Ltd. and/or its affiliates

"""Exit codes for ARVO 2.0"""


class ExitCode:
    """Standard exit codes for ARVO"""
    
    # Success
    SUCCESS = 0
    
    # General errors
    GENERAL_ERROR = 1
    INVALID_ARGUMENTS = 2
    DISK_FULL = 3
    
    # Configuration errors (10-19)
    CONFIGURATION_FAILED = 10
    MAX_TURNS_EXCEEDED = 11
    
    # LLM errors (20-29)
    LLM_ERROR = 20
    LLM_TIMEOUT = 21
    LLM_RATE_LIMIT = 22
    LLM_AUTH_ERROR = 23
    
    # Docker errors (30-39)
    DOCKER_ERROR = 30
    DOCKER_IMAGE_BUILD_FAILED = 31
    DOCKER_CONTAINER_ERROR = 32
    DOCKER_NOT_FOUND = 33
    
    # Repository errors (40-49)
    REPO_CLONE_FAILED = 40
    REPO_CHECKOUT_FAILED = 41
    REPO_NOT_FOUND = 42
    
    # Build errors (50-59)
    BUILD_FAILED = 50
    TEST_VERIFICATION_FAILED = 51
    
    # Timeout errors
    TIMEOUT = 120
    
    @classmethod
    def get_message(cls, code):
        """Get human-readable message for exit code"""
        messages = {
            cls.SUCCESS: "Success",
            cls.GENERAL_ERROR: "General error",
            cls.INVALID_ARGUMENTS: "Invalid arguments",
            cls.DISK_FULL: "Disk full (>90% usage)",
            cls.CONFIGURATION_FAILED: "Configuration failed",
            cls.MAX_TURNS_EXCEEDED: "Max turns exceeded",
            cls.LLM_ERROR: "LLM API error",
            cls.LLM_TIMEOUT: "LLM timeout",
            cls.LLM_RATE_LIMIT: "LLM rate limit exceeded",
            cls.LLM_AUTH_ERROR: "LLM authentication error",
            cls.DOCKER_ERROR: "Docker error",
            cls.DOCKER_IMAGE_BUILD_FAILED: "Docker image build failed",
            cls.DOCKER_CONTAINER_ERROR: "Docker container error",
            cls.DOCKER_NOT_FOUND: "Docker not found",
            cls.REPO_CLONE_FAILED: "Repository clone failed",
            cls.REPO_CHECKOUT_FAILED: "Repository checkout failed",
            cls.REPO_NOT_FOUND: "Repository not found",
            cls.BUILD_FAILED: "Build failed",
            cls.TEST_VERIFICATION_FAILED: "Test verification failed",
            cls.TIMEOUT: "Operation timed out",
        }
        return messages.get(code, f"Unknown error code: {code}")

