from typing import Annotated

from pydantic import Field

# Shared "bounded string in a bounded list" aliases -- previously redefined
# independently in patients.py (BoundedStrList) and doctor.py (BoundedTagList)
# with the same shape, just different length caps. Bounds prevent DoS via
# oversized payloads and prompt-injection via unbounded strings.
_BoundedTag = Annotated[str, Field(max_length=50)]
BoundedTagList = Annotated[list[_BoundedTag], Field(max_length=10)]

_BoundedStr = Annotated[str, Field(max_length=100)]
BoundedStrList = Annotated[list[_BoundedStr], Field(max_length=20)]
