from fastapi import HTTPException, status


class ChartNotFound(HTTPException):
    def __init__(self, chart_id: str):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chart {chart_id} not found")


class AnalysisFailed(HTTPException):
    def __init__(self, section: str, detail: str = ""):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed for section '{section}': {detail}",
        )


class InvalidSection(HTTPException):
    def __init__(self, section: str, valid: list[str]):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown section '{section}'. Valid: {valid}",
        )


