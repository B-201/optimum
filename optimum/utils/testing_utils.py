# Copyright 2023 The HuggingFace Inc. team. All rights reserved.
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


import importlib.util
import itertools
import os
import shutil
import subprocess
import sys
import unittest
from collections.abc import MutableMapping
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

import torch

from . import (
    is_accelerate_available,
    is_auto_gptq_available,
    is_datasets_available,
    is_diffusers_available,
    is_sentence_transformers_available,
    is_timm_available,
)


# Used to test the hub
USER = "__DUMMY_OPTIMUM_USER__"


def flatten_dict(dictionary: Dict):
    """
    Flatten a nested dictionaries as a flat dictionary.
    """
    items = []
    for k, v in dictionary.items():
        new_key = k
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v).items())
        else:
            items.append((new_key, v))
    return dict(items)


def require_accelerate(test_case):
    """
    Decorator marking a test that requires accelerate. These tests are skipped when accelerate isn't installed.
    """
    return unittest.skipUnless(is_accelerate_available(), "test requires accelerate")(test_case)


def require_auto_gptq(test_case):
    """
    Decorator marking a test that requires auto-gptq. These tests are skipped when auto-gptq isn't installed.
    """
    return unittest.skipUnless(is_auto_gptq_available(), "test requires auto-gptq")(test_case)


def require_torch_gpu(test_case):
    """Decorator marking a test that requires CUDA and PyTorch."""
    torch_device = "cuda" if torch.cuda.is_available() else "cpu"

    return unittest.skipUnless(torch_device == "cuda", "test requires CUDA")(test_case)


def require_ort_rocm(test_case):
    """Decorator marking a test that requires ROCMExecutionProvider for ONNX Runtime."""
    import onnxruntime as ort

    providers = ort.get_available_providers()

    return unittest.skipUnless("ROCMExecutionProvider" == providers[0], "test requires ROCMExecutionProvider")(
        test_case
    )


def require_hf_token(test_case):
    """
    Decorator marking a test that requires huggingface hub token.
    """
    # is HF_AUTH_TOKEN used instead of HF_TOKEN to avoid huggingface_hub picking it up ?
    hf_token = os.environ.get("HF_AUTH_TOKEN", None)
    if hf_token is None:
        return unittest.skip("test requires hf token as `HF_AUTH_TOKEN` environment variable")(test_case)
    else:
        return test_case


def require_sigopt_token_and_project(test_case):
    """
    Decorator marking a test that requires sigopt API token.
    """
    sigopt_api_token = os.environ.get("SIGOPT_API_TOKEN", None)
    has_sigopt_project = os.environ.get("SIGOPT_PROJECT", None)
    if sigopt_api_token is None or has_sigopt_project is None:
        return unittest.skip("test requires an environment variable `SIGOPT_API_TOKEN` and `SIGOPT_PROJECT`")(
            test_case
        )
    else:
        return test_case


def is_ort_training_available():
    is_ort_train_available = importlib.util.find_spec("onnxruntime.training") is not None

    if importlib.util.find_spec("torch_ort") is not None:
        try:
            is_torch_ort_configured = True
            subprocess.run([sys.executable, "-m", "torch_ort.configure"], shell=False, check=True)
        except subprocess.CalledProcessError:
            is_torch_ort_configured = False

    return is_ort_train_available and is_torch_ort_configured


def require_ort_training(test_case):
    """
    Decorator marking a test that requires onnxruntime-training and torch_ort correctly installed and configured.
    These tests are skipped otherwise.
    """
    return unittest.skipUnless(
        is_ort_training_available(),
        "test requires torch_ort correctly installed and configured",
    )(test_case)


def require_diffusers(test_case):
    return unittest.skipUnless(is_diffusers_available(), "test requires diffusers")(test_case)


def require_timm(test_case):
    return unittest.skipUnless(is_timm_available(), "test requires timm")(test_case)


def require_sentence_transformers(test_case):
    return unittest.skipUnless(is_sentence_transformers_available(), "test requires sentence-transformers")(test_case)


def require_datasets(test_case):
    return unittest.skipUnless(is_datasets_available(), "test requires datasets")(test_case)


def grid_parameters(
    parameters: Dict[str, Iterable[Any]],
    yield_dict: bool = False,
    add_test_name: bool = True,
    filter_params_func: Optional[Callable[[Tuple], Tuple]] = None,
) -> Iterable:
    """
    Generates an iterable over the grid of all combinations of parameters.

    Args:
        `parameters` (`Dict[str, Iterable[Any]]`):
            Dictionary of multiple values to generate a grid from.
        `yield_dict` (`bool`, defaults to `False`):
            If True, a dictionary with all keys, and sampled values will be returned. Otherwise, return sampled values as a list.
        `add_test_name` (`bool`, defaults to `True`):
            Whether to add the test name in the yielded list or dictionary.
        filter_params_func (`Optional[Callable[[Tuple], Tuple]]`, defaults to `None`):
            A function that can modify or exclude the current set of parameters. The function should take a tuple of the
            parameters and return the same. If a parameter set is to be excluded, the function should return an empty tuple.
    """
    for params in itertools.product(*parameters.values()):
        if filter_params_func is not None:
            params = filter_params_func(list(params))
            if params is None:
                continue

        test_name = "_".join([str(param) for param in params])
        if yield_dict is True:
            res_dict = {}
            for i, key in enumerate(parameters.keys()):
                res_dict[key] = params[i]
            if add_test_name is True:
                res_dict["test_name"] = test_name
            yield res_dict
        else:
            returned_list = [test_name] + list(params) if add_test_name is True else list(params)
            yield returned_list


def remove_directory(dirpath):
    """
    Remove a directory and its content.
    This is a cross-platform solution to remove a directory and its content that avoids the use of `shutil.rmtree` on Windows.
    Reference: https://github.com/python/cpython/issues/107408
    """
    if os.path.exists(dirpath) and os.path.isdir(dirpath):
        if os.name == "nt":
            os.system(f"rmdir /S /Q {dirpath}")
        else:
            shutil.rmtree(dirpath)
