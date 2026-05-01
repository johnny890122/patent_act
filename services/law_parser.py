"""
Law parser service for extracting law data from different sources.

Current implementation uses mockup JSON data.
Future implementation will parse truth data from markdown files using LLM.
"""
import os
import json
import logging
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LawDataSource(ABC):
    """Abstract base class for law data sources."""
    
    @abstractmethod
    def load_laws(self) -> List[Dict]:
        """
        Load laws from the data source.
        
        Returns:
            List of dictionaries containing law data
            
        Raises:
            FileNotFoundError: If source file not found
            ValueError: If data format is invalid
            IOError: If file cannot be read
        """
        pass
    
    @abstractmethod
    def get_source_info(self) -> str:
        """Return information about the data source."""
        pass


class MockupDataSource(LawDataSource):
    """Data source that reads from mockup JSON file."""
    
    def __init__(self, file_path: Optional[str] = None):
        """
        Initialize mockup data source.
        
        Args:
            file_path: Path to mockup JSON file. If None, uses default path.
        """
        if file_path is None:
            # Default to knowledge/mock_laws.json
            base_dir = os.path.dirname(os.path.dirname(__file__))
            file_path = os.path.join(base_dir, 'knowledge', 'mock_laws.json')
        
        self.file_path = file_path
        logger.debug(f"MockupDataSource initialized with path: {file_path}")
    
    def load_laws(self) -> List[Dict]:
        """Load laws from mockup JSON file."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Mockup data file not found: {self.file_path}")
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                mock_laws = json.load(f)
            
            if not isinstance(mock_laws, list):
                raise ValueError("Invalid data format: expected a list of laws")
            
            logger.info(f"Loaded {len(mock_laws)} laws from {self.file_path}")
            return mock_laws
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except IOError as e:
            logger.error(f"File read error: {str(e)}")
            raise IOError(f"File read error: {str(e)}")
    
    def get_source_info(self) -> str:
        """Return information about the data source."""
        return f"Mockup JSON file: {self.file_path}"


class TruthDataSource(LawDataSource):
    """
    Data source that parses truth data from markdown files using LLM.
    
    This is a placeholder for future implementation.
    Will use LLM to parse knowledge/ch1.md and extract real law articles.
    """
    
    def __init__(self, file_path: Optional[str] = None, llm_config: Optional[Dict] = None):
        """
        Initialize truth data source.
        
        Args:
            file_path: Path to markdown file. If None, uses default path.
            llm_config: Configuration for LLM service (API key, model, etc.)
        """
        if file_path is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            file_path = os.path.join(base_dir, 'knowledge', 'ch1.md')
        
        self.file_path = file_path
        self.llm_config = llm_config or {}
        logger.debug(f"TruthDataSource initialized with path: {file_path}")
    
    def load_laws(self) -> List[Dict]:
        """
        Parse markdown file using LLM and extract real law data.
        
        TODO: Implement LLM-based parsing in future phase.
        For now, raises NotImplementedError.
        """
        raise NotImplementedError(
            "LLM-based markdown parsing is not yet implemented. "
            "This will be developed in a future phase. "
            "Please use MockupDataSource for now."
        )
    
    def get_source_info(self) -> str:
        """Return information about the data source."""
        return f"Truth data (Markdown + LLM parser): {self.file_path}"


class LawParserService:
    """
    Service for parsing and loading law data from various sources.
    
    This service acts as a facade, providing a unified interface for
    loading law data regardless of the underlying source.
    """
    
    def __init__(self, data_source: Optional[LawDataSource] = None):
        """
        Initialize law parser service.
        
        Args:
            data_source: Data source to use. If None, uses MockupDataSource.
        """
        if data_source is None:
            data_source = MockupDataSource()
        
        self.data_source = data_source
        logger.info(f"LawParserService initialized with: {data_source.get_source_info()}")
    
    def load_laws(self) -> List[Dict]:
        """
        Load laws from the configured data source.
        
        Returns:
            List of dictionaries containing law data
            
        Raises:
            FileNotFoundError: If source file not found
            ValueError: If data format is invalid
            IOError: If file cannot be read
            NotImplementedError: If data source is not yet implemented
        """
        logger.info("Loading laws from data source")
        laws = self.data_source.load_laws()
        logger.info(f"Successfully loaded {len(laws)} laws")
        return laws
    
    def get_source_info(self) -> str:
        """Get information about the current data source."""
        return self.data_source.get_source_info()
    
    @staticmethod
    def create_mockup_source(file_path: Optional[str] = None) -> 'LawParserService':
        """
        Factory method to create a service with mockup JSON data source.
        
        Args:
            file_path: Optional path to mockup JSON file
            
        Returns:
            LawParserService configured with MockupDataSource
        """
        return LawParserService(MockupDataSource(file_path))
    
    @staticmethod
    def create_truth_source(file_path: Optional[str] = None, llm_config: Optional[Dict] = None) -> 'LawParserService':
        """
        Factory method to create a service with truth data parser (Markdown + LLM).
        
        Args:
            file_path: Optional path to markdown file
            llm_config: Optional LLM configuration
            
        Returns:
            LawParserService configured with TruthDataSource
            
        Note:
            This will raise NotImplementedError when load_laws() is called
            until the LLM parser is implemented in a future phase.
        """
        return LawParserService(TruthDataSource(file_path, llm_config))
