# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A test for the function analyzer agent."""

import argparse
import logging
import multiprocessing
import os
from typing import List

import run_all_experiments
from agent import function_analyzer
from experiment import benchmark as benchmarklib
from experiment import workdir
from llm_toolkit import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RESULTS_DIR = './results'

NUM_ANA = int(os.getenv('LLM_NUM_ANA', '2'))


def parse_args() -> argparse.Namespace:
  """Parses command line arguments."""
  parser = argparse.ArgumentParser(
      description='Evaluate the function analyzer agent.')

  parser.add_argument('-y',
                      '--benchmark-yaml',
                      type=str,
                      help='A benchmark YAML file.')

  parser.add_argument('-b',
                      '--benchmarks-directory',
                      type=str,
                      help='A directory containing benchmark YAML files.')

  parser.add_argument(
      '-g',
      '--generate-benchmarks',
      help=('Generate benchmarks and use those for analysis. This is a string '
            'of comma-separated heuristics to use when identifying benchmark '
            'targets.'),
      type=str)

  parser.add_argument('-np',
                      '--num-pools',
                      type=int,
                      default=NUM_ANA,
                      help='Number of parallel processes to use for analysis.')

  parser.add_argument('-w', '--work-dir', default=RESULTS_DIR)

  parser.add_argument('-mr',
                      '--max-round',
                      type=int,
                      default=100,
                      help='Max trial round for agents.')

  parsed_args = parser.parse_args()

  benchmark_yaml = parsed_args.benchmark_yaml
  if benchmark_yaml:
    assert (benchmark_yaml.endswith('.yaml') or
            benchmark_yaml.endswith('yml')), (
                '--benchmark-yaml needs to take an YAML file.')

  bench_yml = bool(benchmark_yaml)
  bench_dir = bool(parsed_args.benchmarks_directory)
  bench_gen = bool(parsed_args.generate_benchmarks)

  num_options = int(bench_yml) + int(bench_dir) + int(bench_gen)
  assert num_options == 1, (
      'One and only one of --benchmark-yaml, --benchmarks-directory and '
      '--generate-benchmarks. --benchmark-yaml takes one benchmark YAML file, '
      '--benchmarks-directory takes: a directory of them and '
      '--generate-benchmarks generates them during analysis.')

  return parsed_args


def analyze_benchmark(benchmark: benchmarklib.Benchmark, model: models.LLM,
                      args: argparse.Namespace) -> bool:
  """Analyzes the benchmark using the function analyzer."""

  # Initialize the function analyzer
  analyzer = function_analyzer.FunctionAnalyzer(trial=1,
                                                llm=model,
                                                args=args,
                                                benchmark=benchmark)

  # Run the function analyzer
  try:
    result = analyzer.execute([])
  except Exception as e:
    logger.error('Error during analysis for benchmark %s: %s',
                 benchmark.function_name, e)
    return False

  return result.function_analysis is not None


if __name__ == '__main__':

  model = models.LLM.setup(ai_binary='', name='vertex_ai_gemini-2-5-pro-chat')

  args = parse_args()

  # Initialize the working directory
  args.work_dirs = workdir.WorkDirs(args.work_dir)

  # Initialize benchmarks
  benchmarks: List[
      benchmarklib.Benchmark] = run_all_experiments.prepare_experiment_targets(
          args)

  if len(benchmarks) == 0:
    raise ValueError('No benchmarks found in the YAML file.')

  logger.info('Loaded %d benchmarks from the YAML file %s.', len(benchmarks),
              args.benchmark_yaml)

  # Analyze each benchmark
  success_count = 0

  if NUM_ANA == 1:
    for benchmark in benchmarks:
      logger.info('Loaded benchmark (%d/%d) for function: %s',
                  benchmarks.index(benchmark) + 1, len(benchmarks),
                  benchmark.function_name)
      if analyze_benchmark(benchmark, model, args):
        success_count += 1
  else:

    logger.info('Running analysis in parallel with %d processes.',
                args.num_pools)
    with multiprocessing.Pool(args.num_pools, maxtasksperchild=1) as pool:

      results = {}
      for benchmark in benchmarks:
        # Pass a new analyzer instance to each process to avoid sharing state
        logger.info('Submitted benchmark (%d/%d) for function: %s to the pool.',
                    benchmarks.index(benchmark) + 1, len(benchmarks),
                    benchmark.function_name)
        result = pool.apply_async(analyze_benchmark,
                                  args=(benchmark, model, args))
        results[benchmark.id] = result

      pool.close()

      # Wait for all processes to complete
      pool.join()

      # Wait for all results to complete and count successes
      for benchmark_id, result in results.items():
        try:
          if result.get():
            success_count += 1
        except Exception as e:
          logger.error('Error during analysis for benchmark %s: %s',
                       benchmark_id, e)

  print(
      f"{success_count} out of {len(benchmarks)} analyses completed successfully."
  )
