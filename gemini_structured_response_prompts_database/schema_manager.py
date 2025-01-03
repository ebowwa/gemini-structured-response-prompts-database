"""
Core schema management functionality for Gemini prompts
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional, Union

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy import Table

from .models import PromptSchema, PromptResponse, PromptSchemaDB, PromptResponseDB
from .database import Database

logger = logging.getLogger(__name__)

class SchemaManager:
    """Manages prompt schemas and their configurations"""
    
    DEFAULT_PROMPT_TYPE = "example_prompt"
    DEFAULT_PROMPT_TEXT = (
        "This is an example prompt. The response schema should be defined "
        "based on your specific use case and the expected structure of the response."
    )
    DEFAULT_RESPONSE_SCHEMA = {
        "type": "object",
        "description": "Dynamic response schema - define based on your needs",
        "additionalProperties": True
    }
    
    def __init__(
        self,
        database: Optional[Database] = None,
        table: Optional[Table] = None,
        default_prompt_type: Optional[str] = None,
        default_prompt_text: Optional[str] = None,
        default_response_schema: Optional[Dict] = None
    ):
        """Initialize SchemaManager with optional custom database and defaults"""
        self.database = database
        self.table = table
        self.default_prompt_type = default_prompt_type or self.DEFAULT_PROMPT_TYPE
        self.default_prompt_text = default_prompt_text or self.DEFAULT_PROMPT_TEXT
        self.default_response_schema = default_response_schema or self.DEFAULT_RESPONSE_SCHEMA
    
    def _db_to_pydantic(self, db_model: Union[PromptSchemaDB, PromptResponseDB]) -> Union[PromptSchema, PromptResponse]:
        """Convert SQLAlchemy model to Pydantic model"""
        if isinstance(db_model, PromptSchemaDB):
            return PromptSchema.model_validate(db_model)
        elif isinstance(db_model, PromptResponseDB):
            return PromptResponse.model_validate(db_model)
        raise ValueError(f"Unknown model type: {type(db_model)}")
    
    def _pydantic_to_db(self, pydantic_model: Union[PromptSchema, PromptResponse]) -> Union[PromptSchemaDB, PromptResponseDB]:
        """Convert Pydantic model to SQLAlchemy model"""
        data = pydantic_model.model_dump()
        if isinstance(pydantic_model, PromptSchema):
            return PromptSchemaDB(**data)
        elif isinstance(pydantic_model, PromptResponse):
            return PromptResponseDB(**data)
        raise ValueError(f"Unknown model type: {type(pydantic_model)}")

    async def get_prompt_schema(self, prompt_type: str) -> PromptSchema:
        """Get a prompt schema by type"""
        try:
            result = await self.database.get_schema(prompt_type)
            if not result:
                raise HTTPException(status_code=404, detail=f"Schema not found for type: {prompt_type}")
            return self._db_to_pydantic(result)
        except Exception as e:
            logger.error(f"Error getting schema: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get schema: {str(e)}")

    async def create_prompt_schema(
        self,
        prompt_type: str,
        prompt_text: str,
        response_schema: Dict,
        **kwargs
    ) -> PromptSchema:
        """Create a new prompt schema"""
        try:
            schema = PromptSchema(
                prompt_type=prompt_type,
                prompt_text=prompt_text,
                response_schema=response_schema,
                created_at=int(datetime.now().timestamp()),
                **kwargs
            )
            db_schema = self._pydantic_to_db(schema)
            result = await self.database.create_schema(db_schema)
            return self._db_to_pydantic(result)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating schema: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to create schema: {str(e)}")

    async def update_prompt_schema(
        self,
        prompt_type: str,
        prompt_text: Optional[str] = None,
        response_schema: Optional[Dict] = None,
        **kwargs
    ) -> PromptSchema:
        """Update an existing prompt schema"""
        try:
            existing = await self.database.get_schema(prompt_type)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Schema not found for type: {prompt_type}")
            
            update_data = {
                "prompt_type": prompt_type,
                "prompt_text": prompt_text or existing.prompt_text,
                "response_schema": response_schema or existing.response_schema,
                "updated_at": int(datetime.now().timestamp()),
                **kwargs
            }
            
            schema = PromptSchema(**update_data)
            db_schema = self._pydantic_to_db(schema)
            result = await self.database.update_schema(db_schema)
            return self._db_to_pydantic(result)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating schema: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to update schema: {str(e)}")

    async def delete_prompt_schema(self, prompt_type: str) -> bool:
        """Delete a prompt schema"""
        try:
            await self.database.delete_schema(prompt_type)
            return True
        except Exception as e:
            logger.error(f"Error deleting schema: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to delete schema: {str(e)}")
