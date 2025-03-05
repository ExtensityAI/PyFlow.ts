from pyflow import extensity
from pyflow.core import registry
from typing import List, Dict, Any, Optional, Union
import datetime
import json
import statistics

@extensity
class DataPoint:
    timestamp: datetime.datetime
    value: float
    tags: Optional[Dict[str, str]]

    def __init__(self, timestamp: Union[str, datetime.datetime], value: float, tags: Optional[Dict[str, str]] = None):
        if isinstance(timestamp, str):
            self.timestamp = datetime.datetime.fromisoformat(timestamp)
        else:
            self.timestamp = timestamp
        self.value = value
        self.tags = tags or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "tags": self.tags
        }

    def print(self) -> None:
        print(json.dumps(self.to_dict(), indent=4))

class MyType:
    value: int
    value2: str
    # ...

class DataSeries:
    name: str
    data_points: Optional[List[DataPoint]]

    def __init__(self, name: str, data_points: Optional[List[DataPoint]] = None):
        self.name = name
        self.data_points = data_points or []

    @extensity
    def add_point(self, point: DataPoint) -> None:
        self.data_points.append(point)

    @extensity
    def add_points(self, points: List[DataPoint]) -> None:
        self.data_points.extend(points)

    @extensity
    def get_points(self) -> List[Dict[str, Any]]:
        return [point.to_dict() for point in self.data_points]

    @extensity
    def get_my_type(self) -> MyType:
        return MyType(value=42, value2="hello")

    @extensity
    def set_my_type(self, my_type: MyType) -> None:
        print("Setting MyType:", my_type)

    def clear(self) -> None:
        self.data_points = []

    def get_statistics(self) -> Dict[str, Any]:
        if not self.data_points:
            return {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "median": None
            }

        values = [point.value for point in self.data_points]

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values)
        }

# Explicitly register the DataSeries class
registry.register_class(DataSeries, DataSeries.__module__)

@extensity
def create_data_point(timestamp: str, value: float, tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create a data point and return it as a dictionary."""
    point = DataPoint(timestamp, value, tags)
    return point.to_dict()

@extensity
def analyze_data_series(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze a data series."""
    # Convert dictionaries to DataPoint objects
    points = [DataPoint(point["timestamp"], point["value"], point.get("tags")) for point in data]

    # Create a temporary DataSeries
    series = DataSeries("temp", points)

    # Get statistics
    stats = series.get_statistics()

    # Group by tags
    tag_groups = {}
    for point in points:
        for tag_key, tag_value in point.tags.items():
            if tag_key not in tag_groups:
                tag_groups[tag_key] = {}

            if tag_value not in tag_groups[tag_key]:
                tag_groups[tag_key][tag_value] = []

            tag_groups[tag_key][tag_value].append(point.value)

    # Calculate statistics for each tag group
    tag_stats = {}
    for tag_key, value_groups in tag_groups.items():
        tag_stats[tag_key] = {}

        for tag_value, values in value_groups.items():
            tag_stats[tag_key][tag_value] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values)
            }

    return {
        "overall": stats,
        "by_tag": tag_stats
    }
