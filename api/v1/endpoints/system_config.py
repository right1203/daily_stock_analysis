# -*- coding: utf-8 -*-
"""System configuration endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_system_config_service
from api.v1.schemas.common import ErrorResponse
from api.v1.schemas.system_config import (
    SystemConfigConflictResponse,
    SystemConfigResponse,
    SystemConfigSchemaResponse,
    SystemConfigValidationErrorResponse,
    UpdateSystemConfigRequest,
    UpdateSystemConfigResponse,
    ValidateSystemConfigRequest,
    ValidateSystemConfigResponse,
)
from src.services.system_config_service import ConfigConflictError, ConfigValidationError, SystemConfigService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/config",
    response_model=SystemConfigResponse,
    responses={
        200: {"description": "설정을 불러왔습니다"},
        401: {"description": "인증이 필요합니다", "model": ErrorResponse},
        500: {"description": "서버 내부 오류", "model": ErrorResponse},
    },
    summary="시스템 설정 조회",
    description=".env에서 현재 설정을 읽어 원본 값을 반환합니다.",
)
def get_system_config(
    include_schema: bool = Query(True, description="스키마 메타데이터를 포함할지 여부입니다."),
    service: SystemConfigService = Depends(get_system_config_service),
) -> SystemConfigResponse:
    """Load and return current system configuration."""
    try:
        payload = service.get_config(include_schema=include_schema)
        return SystemConfigResponse.model_validate(payload)
    except Exception as exc:
        logger.error("Failed to load system configuration: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "시스템 설정을 불러오지 못했습니다",
            },
        )


@router.put(
    "/config",
    response_model=UpdateSystemConfigResponse,
    responses={
        200: {"description": "설정이 업데이트되었습니다"},
        400: {"description": "검증에 실패했습니다", "model": SystemConfigValidationErrorResponse},
        409: {"description": "버전 충돌", "model": SystemConfigConflictResponse},
        500: {"description": "서버 내부 오류", "model": ErrorResponse},
    },
    summary="시스템 설정 업데이트",
    description=".env의 키-값 설정을 업데이트합니다. 마스킹 토큰은 기존 비밀 값을 유지합니다.",
)
def update_system_config(
    request: UpdateSystemConfigRequest,
    service: SystemConfigService = Depends(get_system_config_service),
) -> UpdateSystemConfigResponse:
    """Validate and persist system configuration updates."""
    try:
        payload = service.update(
            config_version=request.config_version,
            items=[item.model_dump() for item in request.items],
            mask_token=request.mask_token,
            reload_now=request.reload_now,
        )
        return UpdateSystemConfigResponse.model_validate(payload)
    except ConfigValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_failed",
                "message": "시스템 설정 검증에 실패했습니다",
                "issues": exc.issues,
            },
        )
    except ConfigConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "config_version_conflict",
                "message": "설정이 변경되었습니다. 다시 불러온 뒤 재시도하세요",
                "current_config_version": exc.current_version,
            },
        )
    except Exception as exc:
        logger.error("Failed to update system configuration: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "시스템 설정을 업데이트하지 못했습니다",
            },
        )


@router.post(
    "/config/validate",
    response_model=ValidateSystemConfigResponse,
    responses={
        200: {"description": "검증이 완료되었습니다"},
        500: {"description": "서버 내부 오류", "model": ErrorResponse},
    },
    summary="시스템 설정 검증",
    description=".env에 기록하지 않고 제출된 설정 값을 검증합니다.",
)
def validate_system_config(
    request: ValidateSystemConfigRequest,
    service: SystemConfigService = Depends(get_system_config_service),
) -> ValidateSystemConfigResponse:
    """Run pre-save validation only."""
    try:
        payload = service.validate(items=[item.model_dump() for item in request.items])
        return ValidateSystemConfigResponse.model_validate(payload)
    except Exception as exc:
        logger.error("Failed to validate system configuration: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "시스템 설정을 검증하지 못했습니다",
            },
        )


@router.get(
    "/config/schema",
    response_model=SystemConfigSchemaResponse,
    responses={
        200: {"description": "스키마를 불러왔습니다"},
        500: {"description": "서버 내부 오류", "model": ErrorResponse},
    },
    summary="시스템 설정 스키마 조회",
    description="동적 설정 폼 렌더링에 사용하는 분류별 필드 메타데이터를 반환합니다.",
)
def get_system_config_schema(
    service: SystemConfigService = Depends(get_system_config_service),
) -> SystemConfigSchemaResponse:
    """Return schema metadata for system configuration fields."""
    try:
        payload = service.get_schema()
        return SystemConfigSchemaResponse.model_validate(payload)
    except Exception as exc:
        logger.error("Failed to load system configuration schema: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "시스템 설정 스키마를 불러오지 못했습니다",
            },
        )
