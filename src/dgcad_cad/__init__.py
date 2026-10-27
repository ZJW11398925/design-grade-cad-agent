"""Living CAD-IR and DXF delivery layer for the E2E slice."""

from .dxf import (
    XDATA_APPID,
    XDATA_FIELDS,
    DxfCompileResult,
    compile_to_dxf,
)
from .ir import (
    CAD_COVERAGE_LIMITS,
    CAD_IR_SCHEMA_ID,
    CadIR,
    CadIssue,
    CadObject,
    CadValidationResult,
    DeliveryProfile,
    build_cad_ir,
    validate_cad_ir,
)
from .validator import (
    COVERAGE_LIMITS,
    DxfIssue,
    DxfReadbackResult,
    validate_dxf,
)

__all__ = [
    "CAD_COVERAGE_LIMITS",
    "CAD_IR_SCHEMA_ID",
    "COVERAGE_LIMITS",
    "CadIR",
    "CadIssue",
    "CadObject",
    "CadValidationResult",
    "DeliveryProfile",
    "DxfCompileResult",
    "DxfIssue",
    "DxfReadbackResult",
    "XDATA_APPID",
    "XDATA_FIELDS",
    "build_cad_ir",
    "compile_to_dxf",
    "validate_cad_ir",
    "validate_dxf",
]
