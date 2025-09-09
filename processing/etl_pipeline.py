from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, avg, year, month
import os

def run_etl(input_path="data/raw", output_path="data/processed"):
    spark = SparkSession.builder.appName("Sofia Air Quality ETL").getOrCreate()

    # Weather files
    weather_files = [os.path.join(input_path, f) for f in os.listdir(input_path) if "bme280sof" in f]
    df_weather = spark.read.csv(weather_files, header=True, inferSchema=True)
    df_weather = df_weather.withColumn("date", to_date(col("timestamp")))
    df_weather = df_weather.select("timestamp", "location", "lat", "lon", "date", "temperature", "humidity", "pressure").dropna()

    # Pollution files
    pollutant_files = [os.path.join(input_path, f) for f in os.listdir(input_path) if "sds011sof" in f]
    df_pollution = spark.read.csv(pollutant_files, header=True, inferSchema=True)
    df_pollution = df_pollution.withColumn("date", to_date(col("timestamp")))
    df_pollution = df_pollution.select("timestamp", "location", "lat", "lon", "date",
                                       col("P1").alias("PM10"),
                                       col("P2").alias("PM2_5")).dropna()

    # Join & aggregate
    df_joined = df_pollution.join(df_weather, ["timestamp", "location", "lat", "lon", "date"], "inner")
    daily_avg = df_joined.groupBy("location", "lat", "lon", "date").agg(
        avg("PM10").alias("avg_PM10"),
        avg("PM2_5").alias("avg_PM2_5"),
        avg("temperature").alias("avg_temperature"),
        avg("humidity").alias("avg_humidity"),
        avg("pressure").alias("avg_pressure")
    ).withColumn("year", year("date")).withColumn("month", month("date"))

    # Save parquet
    daily_avg.write.mode("overwrite").partitionBy("year", "month").parquet(output_path)
    spark.stop()
    print(f"ETL completed. Processed data saved to {output_path}")
