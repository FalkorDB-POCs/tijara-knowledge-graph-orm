"""
Dimensional Extraction - Convert graph data to tabular format
"""

from typing import Dict, List, Optional, Any
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class DimensionalExtractor:
    """
    Extracts dimensional data from the graph and converts to tabular format.
    Useful for analytics, reporting, and integration with BI tools.
    """
    
    def __init__(self, falkordb_client):
        """
        Initialize dimensional extractor.
        
        Args:
            falkordb_client: FalkorDB client instance
        """
        self.db = falkordb_client
    
    def extract_to_dataframe(
        self,
        entity_type: str,
        dimensions: List[str],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10000
    ) -> pd.DataFrame:
        """
        Extract graph data to pandas DataFrame.
        
        Args:
            entity_type: Type of entity to extract
            dimensions: List of properties/dimensions to include
            filters: Optional filters to apply
            limit: Maximum number of rows
            
        Returns:
            pandas DataFrame with extracted data
        """
        logger.info(f"Extracting {entity_type} to DataFrame with dimensions: {dimensions}")
        
        try:
            # Build Cypher query
            query = self._build_extraction_query(entity_type, dimensions, filters, limit)
            
            # Execute query
            results = self.db.execute_query(query) if hasattr(self.db, 'execute_query') else []
            
            # Convert to DataFrame
            if results:
                df = pd.DataFrame(results)
                return df
            else:
                # Return empty DataFrame with correct columns
                return pd.DataFrame(columns=dimensions)
        
        except Exception as e:
            logger.error(f"Error extracting to DataFrame: {e}")
            return pd.DataFrame(columns=dimensions)
    
    def extract_time_series(
        self,
        entity_id: str,
        value_property: str = "value",
        time_property: str = "year",
        filters: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Extract time series data for an entity.
        
        Args:
            entity_id: Entity ID
            value_property: Property containing values
            time_property: Property containing time information
            filters: Optional filters
            
        Returns:
            DataFrame with time series data
        """
        logger.info(f"Extracting time series for entity {entity_id}")
        
        try:
            query = f"""
            MATCH (n)-[:HAS_DATA]->(d)
            WHERE id(n) = '{entity_id}'
            RETURN d.{time_property} as time, d.{value_property} as value
            ORDER BY d.{time_property}
            """
            
            results = self.db.execute_query(query) if hasattr(self.db, 'execute_query') else []
            
            if results:
                df = pd.DataFrame(results)
                if 'time' in df.columns:
                    df['time'] = pd.to_datetime(df['time'])
                return df
            else:
                return pd.DataFrame(columns=['time', 'value'])
        
        except Exception as e:
            logger.error(f"Error extracting time series: {e}")
            return pd.DataFrame(columns=['time', 'value'])
    
    def extract_relationships(
        self,
        relationship_type: str,
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10000
    ) -> pd.DataFrame:
        """
        Extract relationships as a DataFrame.
        
        Args:
            relationship_type: Type of relationship to extract
            source_type: Optional source entity type filter
            target_type: Optional target entity type filter
            filters: Optional filters
            limit: Maximum number of relationships
            
        Returns:
            DataFrame with relationship data
        """
        logger.info(f"Extracting {relationship_type} relationships")
        
        try:
            source_filter = f":{source_type}" if source_type else ""
            target_filter = f":{target_type}" if target_type else ""
            
            query = f"""
            MATCH (a{source_filter})-[r:{relationship_type}]->(b{target_filter})
            RETURN id(a) as source_id, id(b) as target_id, 
                   labels(a)[0] as source_type, labels(b)[0] as target_type,
                   properties(r) as properties
            LIMIT {limit}
            """
            
            results = self.db.execute_query(query) if hasattr(self.db, 'execute_query') else []
            
            if results:
                return pd.DataFrame(results)
            else:
                return pd.DataFrame(columns=['source_id', 'target_id', 'source_type', 'target_type'])
        
        except Exception as e:
            logger.error(f"Error extracting relationships: {e}")
            return pd.DataFrame(columns=['source_id', 'target_id', 'source_type', 'target_type'])
    
    def pivot_by_geography(
        self,
        indicator: str,
        commodity: Optional[str] = None,
        year: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Create a pivot table by geography for a specific indicator.
        
        Args:
            indicator: Indicator type (e.g., "Production", "Exports")
            commodity: Optional commodity filter
            year: Optional year filter
            
        Returns:
            Pivoted DataFrame with geographies as rows
        """
        logger.info(f"Creating pivot table for {indicator}")
        
        try:
            filters = {'indicator': indicator}
            if commodity:
                filters['commodity'] = commodity
            if year:
                filters['year'] = year
            
            # Extract data
            df = self.extract_to_dataframe(
                entity_type=indicator,
                dimensions=['geography', 'commodity', 'year', 'value'],
                filters=filters
            )
            
            if not df.empty and 'geography' in df.columns:
                # Create pivot table
                pivot = df.pivot_table(
                    values='value',
                    index='geography',
                    columns='commodity' if 'commodity' in df.columns else None,
                    aggfunc='sum'
                )
                return pivot
            else:
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error creating pivot table: {e}")
            return pd.DataFrame()
    
    def aggregate_by_dimension(
        self,
        entity_type: str,
        dimension: str,
        aggregation: str = "sum",
        value_property: str = "value",
        filters: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Aggregate data by a specific dimension.
        
        Args:
            entity_type: Type of entity
            dimension: Dimension to group by
            aggregation: Aggregation function (sum, avg, count, min, max)
            value_property: Property to aggregate
            filters: Optional filters
            
        Returns:
            Aggregated DataFrame
        """
        logger.info(f"Aggregating {entity_type} by {dimension}")
        
        try:
            # Map aggregation to Cypher function
            agg_func_map = {
                'sum': 'sum',
                'avg': 'avg',
                'count': 'count',
                'min': 'min',
                'max': 'max'
            }
            cypher_func = agg_func_map.get(aggregation, 'sum')
            
            # Build filter clause
            where_clause = self._build_where_clause(filters)
            
            query = f"""
            MATCH (n:{entity_type})
            {where_clause}
            RETURN n.{dimension} as {dimension}, {cypher_func}(n.{value_property}) as aggregated_value
            ORDER BY aggregated_value DESC
            """
            
            results = self.db.execute_query(query) if hasattr(self.db, 'execute_query') else []
            
            if results:
                return pd.DataFrame(results)
            else:
                return pd.DataFrame(columns=[dimension, 'aggregated_value'])
        
        except Exception as e:
            logger.error(f"Error aggregating data: {e}")
            return pd.DataFrame(columns=[dimension, 'aggregated_value'])
    
    def _build_extraction_query(
        self,
        entity_type: str,
        dimensions: List[str],
        filters: Optional[Dict[str, Any]],
        limit: int
    ) -> str:
        """Build Cypher query for data extraction"""
        # Build RETURN clause
        return_parts = [f"n.{dim} as {dim}" for dim in dimensions]
        return_clause = ", ".join(return_parts)
        
        # Build WHERE clause
        where_clause = self._build_where_clause(filters)
        
        query = f"""
        MATCH (n:{entity_type})
        {where_clause}
        RETURN {return_clause}
        LIMIT {limit}
        """
        
        return query
    
    def _build_where_clause(self, filters: Optional[Dict[str, Any]]) -> str:
        """Build WHERE clause from filters"""
        if not filters:
            return ""
        
        conditions = []
        for key, value in filters.items():
            if isinstance(value, str):
                conditions.append(f"n.{key} = '{value}'")
            else:
                conditions.append(f"n.{key} = {value}")
        
        if conditions:
            return "WHERE " + " AND ".join(conditions)
        return ""
    
    def export_to_csv(
        self,
        entity_type: str,
        dimensions: List[str],
        output_path: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10000
    ) -> bool:
        """
        Export graph data to CSV file.
        
        Args:
            entity_type: Type of entity to extract
            dimensions: List of properties to include
            output_path: Path to output CSV file
            filters: Optional filters
            limit: Maximum number of rows
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Exporting {entity_type} to CSV: {output_path}")
        
        try:
            df = self.extract_to_dataframe(entity_type, dimensions, filters, limit)
            df.to_csv(output_path, index=False)
            logger.info(f"Successfully exported {len(df)} rows to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False
