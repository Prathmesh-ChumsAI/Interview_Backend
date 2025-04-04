from pydantic import BaseModel, Field
from typing import List
#  Define models for ScoreCard criteria (for typing purposes)
class Criteria(BaseModel):
    parameter: str = Field(..., description="Evaluation parameter")
    top_score: int = Field(..., gt=0, description="Maximum score")
    marking_type: str = Field(..., description="Marking type: 'Pass/Fail' or numeric")
    scoring_guide: str = Field(..., description="Scoring guide")

class ScoreCard(BaseModel):
    name: str
    criterias: List[Criteria]
    created_company: str