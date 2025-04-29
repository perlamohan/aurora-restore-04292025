#!/usr/bin/env python3
"""
Base handler class for Aurora restore Lambda functions.
Provides common functionality and error handling for all Lambda functions.
"""

import time
import json
import uuid
from typing import Dict, Any, TypeVar, Generic

from utils.config_manager import ConfigManager
from utils.common import logger
from utils.state_utils import (
    save_state,
    log_audit_event,
    update_metrics
)

T = TypeVar('T')

class BaseHandler(Generic[T]):
    """Base handler class for Lambda functions with common functionality."""
    
    def __init__(self, step_name: str):
        """
        Initialize the base handler.
        
        Args:
            step_name: Name of the step being handled (e.g., 'snapshot_check')
        """
        self.step_name = step_name
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_all()
        self.start_time = time.time()
    
    def validate_event(self, event: Dict[str, Any]) -> None:
        """
        Validate the incoming event.
        
        Args:
            event: The Lambda event to validate
            
        Raises:
            ValueError: If event validation fails
        """
        if not isinstance(event, dict):
            raise ValueError("Event must be a dictionary")
    
    def get_operation_id(self, event: Dict[str, Any]) -> str:
        """
        Get or generate operation ID from event.
        
        Args:
            event: Lambda event
            
        Returns:
            str: Operation ID
        """
        if event and isinstance(event, dict):
            if 'operation_id' in event:
                return event['operation_id']
            if 'body' in event and isinstance(event['body'], dict) and 'operation_id' in event['body']:
                return event['body']['operation_id']
        
        return f"op-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    
    def save_initial_state(self, operation_id: str, state_data: Dict[str, Any]) -> None:
        """
        Save initial state for the operation.
        
        Args:
            operation_id: Operation ID
            state_data: State data to save
        """
        save_state(operation_id, self.step_name, state_data)
    
    def log_audit(self, operation_id: str, status: str, details: Dict[str, Any]) -> None:
        """
        Log an audit event.
        
        Args:
            operation_id: Operation ID
            status: Status of the operation
            details: Additional details
        """
        log_audit_event(operation_id, self.step_name, status, details)
    
    def update_metrics(self, operation_id: str, metric_name: str, value: float = 1.0) -> None:
        """
        Update metrics for the operation.
        
        Args:
            operation_id: Operation ID
            metric_name: Name of the metric
            value: Value of the metric
        """
        update_metrics(operation_id, self.step_name, metric_name, value)
    
    def handle_error(self, operation_id: str, error: Exception, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an error in the operation.
        
        Args:
            operation_id: Operation ID
            error: The error that occurred
            details: Additional details
            
        Returns:
            Dict[str, Any]: Error response
        """
        error_message = str(error)
        logger.error(f"Error in {self.step_name}: {error_message}", extra={
            'operation_id': operation_id,
            'step': self.step_name,
            'error': error_message,
            'details': details
        })
        
        self.log_audit(operation_id, 'ERROR', {
            'error': error_message,
            'details': details
        })
        
        return self.create_response(operation_id, {
            'error': error_message,
            'details': details
        }, 500)
    
    def create_response(self, operation_id: str, data: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
        """
        Create a response for the Lambda function.
        
        Args:
            operation_id: Operation ID
            data: Response data
            status_code: HTTP status code
            
        Returns:
            Dict[str, Any]: Lambda response
        """
        return {
            'statusCode': status_code,
            'body': json.dumps({
                'operation_id': operation_id,
                'step': self.step_name,
                'data': data
            })
        }
    
    def execute(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Execute the Lambda function.
        
        Args:
            event: Lambda event
            context: Lambda context
            
        Returns:
            Dict[str, Any]: Lambda response
        """
        try:
            # Validate event
            self.validate_event(event)
            
            # Get operation ID
            operation_id = self.get_operation_id(event)
            
            # Load configuration from event and state
            if 'state' in event:
                self.config_manager.load_config(event=event, state=event['state'])
            else:
                self.config_manager.load_config(event=event)
            
            self.config = self.config_manager.get_all()
            
            # Process the event
            return self.process(event, context)
        except Exception as e:
            # Handle any unhandled exceptions
            operation_id = self.get_operation_id(event) if event else "unknown"
            return self.handle_error(operation_id, e, {})
    
    def process(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Process the Lambda event.
        
        Args:
            event: Lambda event
            context: Lambda context
            
        Returns:
            Dict[str, Any]: Lambda response
            
        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement process method") 