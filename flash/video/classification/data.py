# Copyright The PyTorch Lightning team.
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
import pathlib
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Type, Union

import numpy as np
import torch
from pytorch_lightning.utilities.exceptions import MisconfigurationException
from torch import nn
from torch.nn import Module
from torch.utils.data import Dataset, RandomSampler, Sampler
from torch.utils.data._utils.collate import default_collate
from torch.utils.data.dataset import IterableDataset
from torchvision.datasets.folder import has_file_allowed_extension, IMG_EXTENSIONS, make_dataset

from flash.data.auto_dataset import AutoDataset
from flash.data.data_module import DataModule
from flash.data.data_pipeline import DataPipeline
from flash.data.process import Preprocess
from flash.utils.imports import _KORNIA_AVAILABLE, _PYTORCHVIDEO_AVAILABLE

if _KORNIA_AVAILABLE:
    import kornia.augmentation as K
    import kornia.geometry.transform as T
else:
    from torchvision import transforms as T

if _PYTORCHVIDEO_AVAILABLE:
    from pytorchvideo.data.clip_sampling import ClipSampler, make_clip_sampler
    from pytorchvideo.data.encoded_video_dataset import EncodedVideoDataset, labeled_encoded_video_dataset

_PYTORCHVIDEO_DATA = Dict[str, Union[str, torch.Tensor, int, float, List]]


class VideoClassificationPreprocess(Preprocess):

    def __init__(
        self,
        clip_sampler: 'ClipSampler',
        video_sampler: Type[Sampler],
        decode_audio: bool,
        decoder: str,
        train_transform: Optional[Dict[str, Callable]] = None,
        val_transform: Optional[Dict[str, Callable]] = None,
        test_transform: Optional[Dict[str, Callable]] = None,
        predict_transform: Optional[Dict[str, Callable]] = None,
    ):
        # Make sure to provide your transform to the Preprocess Class
        super().__init__(train_transform, val_transform, test_transform, predict_transform)
        self.clip_sampler = clip_sampler
        self.video_sampler = video_sampler
        self.decode_audio = decode_audio
        self.decoder = decoder

    def load_data(self, data: Any, dataset: IterableDataset) -> 'EncodedVideoDataset':
        ds: EncodedVideoDataset = labeled_encoded_video_dataset(
            data,
            self.clip_sampler,
            video_sampler=self.video_sampler,
            decode_audio=self.decode_audio,
            decoder=self.decoder,
        )
        if self.training:
            dataset.num_classes = len(np.unique([s[1]['label'] for s in ds._labeled_videos]))
        return ds

    def pre_tensor_transform(self, sample: _PYTORCHVIDEO_DATA) -> _PYTORCHVIDEO_DATA:
        return self.current_transform(sample)

    def to_tensor_transform(self, sample: _PYTORCHVIDEO_DATA) -> _PYTORCHVIDEO_DATA:
        return self.current_transform(sample)

    def post_tensor_transform(self, sample: _PYTORCHVIDEO_DATA) -> _PYTORCHVIDEO_DATA:
        return self.current_transform(sample)

    def per_batch_transform(self, sample: _PYTORCHVIDEO_DATA) -> _PYTORCHVIDEO_DATA:
        return self.current_transform(sample)

    def per_batch_transform_on_device(self, sample: _PYTORCHVIDEO_DATA) -> _PYTORCHVIDEO_DATA:
        return self.current_transform(sample)


class VideoClassificationData(DataModule):
    """Data module for Video classification tasks."""

    preprocess_cls = VideoClassificationPreprocess

    @classmethod
    def instantiate_preprocess(
        cls,
        clip_sampler: 'ClipSampler',
        video_sampler: Type[Sampler],
        decode_audio: bool,
        decoder: str,
        train_transform: Optional[Dict[str, Callable]],
        val_transform: Optional[Dict[str, Callable]],
        test_transform: Optional[Dict[str, Callable]],
        predict_transform: Optional[Dict[str, Callable]],
        preprocess_cls: Type[Preprocess] = None,
    ) -> Preprocess:
        """
        """
        preprocess_cls = preprocess_cls or cls.preprocess_cls
        preprocess: Preprocess = preprocess_cls(
            clip_sampler, video_sampler, decode_audio, decoder, train_transform, val_transform, test_transform,
            predict_transform
        )
        return preprocess

    @classmethod
    def from_paths(
        cls,
        train_folder: Optional[Union[str, pathlib.Path]] = None,
        val_folder: Optional[Union[str, pathlib.Path]] = None,
        test_folder: Optional[Union[str, pathlib.Path]] = None,
        predict_folder: Union[str, pathlib.Path] = None,
        clip_sampler: Union[str, 'ClipSampler'] = "random",
        clip_duration: float = 2,
        clip_sampler_kwargs: Dict[str, Any] = None,
        video_sampler: Type[Sampler] = RandomSampler,
        decode_audio: bool = True,
        decoder: str = "pyav",
        train_transform: Optional[Dict[str, Callable]] = None,
        val_transform: Optional[Dict[str, Callable]] = None,
        test_transform: Optional[Dict[str, Callable]] = None,
        predict_transform: Optional[Dict[str, Callable]] = None,
        batch_size: int = 4,
        num_workers: Optional[int] = None,
        preprocess_cls: Optional[Type[Preprocess]] = None,
        **kwargs,
    ) -> 'DataModule':
        """

        Creates a VideoClassificationData object from folders of videos arranged in this way: ::

            train/class_x/xxx.ext
            train/class_x/xxy.ext
            train/class_x/xxz.ext
            train/class_y/123.ext
            train/class_y/nsdf3.ext
            train/class_y/asd932_.ext

        Args:
            train_folder: Path to training folder. Default: None.
            val_folder: Path to validation folder. Default: None.
            test_folder: Path to test folder. Default: None.
            predict_folder: Path to predict folder. Default: None.
            clip_sampler: ClipSampler to be used on videos.
            clip_duration: Clip duration for the clip sampler.
            clip_sampler_kwargs: Extra Clip Sampler arguments.
            video_sampler: Sampler for the internal video container.
                This defines the order videos are decoded and, if necessary, the distributed split.
            decode_audio: Wheter to decode the audio with the video clip.
            decoder: Defines what type of decoder used to decode a video.
            train_transform: Dictionnary of Video Clip transform to use for training set.
            val_transform:  Dictionnary of Video Clip transform to use for validation set.
            test_transform:  Dictionnary of Video Clip transform to use for test set.
            predict_transform:  Dictionnary of Video Clip transform to use for predict set.
            batch_size: Batch size for data loading.
            num_workers: The number of workers to use for parallelized loading.
                Defaults to ``None`` which equals the number of available CPU threads.

        Returns:
            VideoClassificationData: the constructed data module

        Examples:
            >>> img_data = VideoClassificationData.from_paths("train/") # doctest: +SKIP

        """
        if not _PYTORCHVIDEO_AVAILABLE:
            raise ModuleNotFoundError("Please, run `pip install pytorchvideo`.")

        if not clip_sampler_kwargs:
            clip_sampler_kwargs = {}

        if not clip_sampler:
            raise MisconfigurationException(
                "clip_sampler should be provided as a string or ``pytorchvideo.data.clip_sampling.ClipSampler``"
            )

        clip_sampler = make_clip_sampler(clip_sampler, clip_duration, **clip_sampler_kwargs)

        preprocess = cls.instantiate_preprocess(
            clip_sampler,
            video_sampler,
            decode_audio,
            decoder,
            train_transform,
            val_transform,
            test_transform,
            predict_transform,
            preprocess_cls=preprocess_cls,
        )

        return cls.from_load_data_inputs(
            train_load_data_input=train_folder,
            val_load_data_input=val_folder,
            test_load_data_input=test_folder,
            predict_load_data_input=predict_folder,
            batch_size=batch_size,
            num_workers=num_workers,
            preprocess=preprocess,
            use_iterable_auto_dataset=True,
            **kwargs,
        )
