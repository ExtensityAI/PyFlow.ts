import {
  DataPoint,
  DataSeries,
  create_data_point,
  analyze_data_series
} from './generated/complex/data_processor';

async function runDataAnalysis() {
  // Create a data series using Python-generated data points
  const series = new DataSeries("temperature");

  // Create sample data points
  const point1 = await create_data_point(
    "2023-01-01T12:00:00",
    22.5,
    { "location": "living_room", "sensor": "A" }
  );

  const point2 = await create_data_point(
    "2023-01-01T12:30:00",
    23.1,
    { "location": "living_room", "sensor": "A" }
  );

  const point3 = await create_data_point(
    "2023-01-01T12:00:00",
    21.8,
    { "location": "bedroom", "sensor": "B" }
  );

  const point4 = await create_data_point(
    "2023-01-01T12:30:00",
    22.2,
    { "location": "bedroom", "sensor": "B" }
  );

  const point5 = await create_data_point(
    "2023-01-01T12:00:00",
    24.1,
    { "location": "kitchen", "sensor": "C" }
  );

  // Add the points to the data series
  await series.add_points([
    new DataPoint(point1.timestamp, point1.value, point1.tags),
    new DataPoint(point2.timestamp, point2.value, point2.tags),
    new DataPoint(point3.timestamp, point3.value, point3.tags),
    new DataPoint(point4.timestamp, point4.value, point4.tags),
    new DataPoint(point5.timestamp, point5.value, point5.tags)
  ]);

  // Get all points
  const points = await series.get_points();
  console.log("Data points:");
  points.forEach((point, index) => {
    console.log(`${index + 1}. ${point.timestamp}: ${point.value}°C (${JSON.stringify(point.tags)})`);
  });

  // Get statistics
  const stats = await series.get_statistics();
  console.log("\nData statistics:");
  console.log(`Count: ${stats.count}`);
  console.log(`Min: ${stats.min}°C`);
  console.log(`Max: ${stats.max}°C`);
  console.log(`Mean: ${stats.mean.toFixed(2)}°C`);
  console.log(`Median: ${stats.median.toFixed(2)}°C`);

  // Analyze the data series using the Python function
  const analysis = await analyze_data_series(points);

  console.log("\nDetailed analysis:");
  console.log(`Overall mean: ${analysis.overall.mean.toFixed(2)}°C`);

  console.log("\nBy location:");
  const locationStats = analysis.by_tag.location;
  for (const location in locationStats) {
    console.log(`- ${location}: ${locationStats[location].mean.toFixed(2)}°C (${locationStats[location].count} readings)`);
  }

  console.log("\nBy sensor:");
  const sensorStats = analysis.by_tag.sensor;
  for (const sensor in sensorStats) {
    console.log(`- Sensor ${sensor}: ${sensorStats[sensor].mean.toFixed(2)}°C (${sensorStats[sensor].count} readings)`);
  }

  // Clear the data
  await series.clear();
  console.log(`\nSeries cleared. Points remaining: ${(await series.get_points()).length}`);
}

runDataAnalysis().catch(console.error);