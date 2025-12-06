from pydantic import BaseModel, Field

# This file holds Pydantic models for API data contracts.
class BottleneckRequest(BaseModel):
    process_name: str = Field(..., example="Invoice Approval Process")
    activity_name: str = Field(..., example="Managerial Approval")
    metrics: dict = Field(..., example={"Average Wait Time (hours)": 72, "Cases Affected": 850})
    # context: str = Field(..., example="Approval requires managers to log into a separate, slow system.")