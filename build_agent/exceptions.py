# Copyright (2025) Bytedance Ltd. and/or its affiliates

"""Custom exceptions for ARVO 2.0"""


class ArvoException(Exception):
    """Base exception for ARVO"""
    pass


class DockerError(ArvoException):
    """Docker-related errors"""
    pass


class ContainerError(DockerError):
    """Container creation or management errors"""
    pass


class ImageBuildError(DockerError):
    """Docker image build errors"""
    pass


class LLMError(ArvoException):
    """LLM API errors"""
    pass


class LLMTimeoutError(LLMError):
    """LLM API timeout"""
    pass


class LLMRateLimitError(LLMError):
    """LLM API rate limit exceeded"""
    pass


class BuildError(ArvoException):
    """Build failure errors"""
    pass


class ConfigurationError(BuildError):
    """Configuration phase errors"""
    pass


class TestVerificationError(BuildError):
    """Test verification errors"""
    pass


class RepositoryError(ArvoException):
    """Git repository errors"""
    pass


class CloneError(RepositoryError):
    """Repository clone errors"""
    pass


class CheckoutError(RepositoryError):
    """Git checkout errors"""
    pass


class ConfigurationValidationError(ArvoException):
    """Configuration validation errors"""
    pass


class DiskFullError(ArvoException):
    """Disk space exhausted"""
    pass

