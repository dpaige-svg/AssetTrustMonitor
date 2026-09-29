import runpy
import tracemalloc
import time

tracemalloc.start()

print("Starting memory profiling...")
print("Run the program normally and exercise the features you want to test.")
print("Press Ctrl+C when you're finished.\n")

try:
    runpy.run_path("main.py", run_name="__main__")

except KeyboardInterrupt:
    print("\nStopping memory profiling...")

finally:
    snapshot = tracemalloc.take_snapshot()

    print("\n=== TOP MEMORY ALLOCATIONS ===")

    for stat in snapshot.statistics("lineno")[:20]:
        print(stat)

    current, peak = tracemalloc.get_traced_memory()

    print("\n=== MEMORY SUMMARY ===")
    print(f"Current traced memory: {current / 1024 / 1024:.2f} MB")
    print(f"Peak traced memory:    {peak / 1024 / 1024:.2f} MB")

    tracemalloc.stop()