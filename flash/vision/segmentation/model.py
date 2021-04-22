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
from types import FunctionType
from typing import Callable, Dict, Mapping, Optional, Sequence, Tuple, Type, Union

import torch
from torch import nn
from torch.nn import functional as F
from torchmetrics import Accuracy

from flash.core.classification import Classes, ClassificationTask
from flash.core.registry import FlashRegistry
from flash.data.process import Preprocess, Serializer

SEMANTIC_SEGMENTATION_BACKBONES = FlashRegistry("backbones")


class SemanticSegmentation(ClassificationTask):
    """Task that performs semantic segmentation on images.
    """

    backbones: FlashRegistry = SEMANTIC_SEGMENTATION_BACKBONES

    def __init__(
        self,
        num_classes: int,
        backbone: Union[str, Tuple[nn.Module, int]] = "resnet18",
        backbone_kwargs: Optional[Dict] = None,
        head: Optional[Union[FunctionType, nn.Module]] = None,
        pretrained: bool = True,
        loss_fn: Optional[Callable] = None,
        optimizer: Type[torch.optim.Optimizer] = torch.optim.SGD,
        metrics: Optional[Union[Callable, Mapping, Sequence, None]] = None,
        learning_rate: float = 1e-3,
        multi_label: bool = False,
        serializer: Optional[Union[Serializer, Mapping[str, Serializer]]] = None,
    ):

        if metrics is None:
            metrics = Accuracy(subset_accuracy=multi_label)

        if loss_fn is None:
            # loss_fn = binary_cross_entropy_with_logits if multi_label else F.cross_entropy
            loss_fn = F.cross_entropy

        super().__init__(
            model=None,
            loss_fn=loss_fn,
            optimizer=optimizer,
            metrics=metrics,
            learning_rate=learning_rate,
            serializer=serializer or Classes(multi_label=multi_label),
        )

        self.save_hyperparameters()

        if not backbone_kwargs:
            backbone_kwargs = {}

        # TODO: implement first torchvision
        self.backbone, num_features = None, 1
        '''if isinstance(backbone, tuple):
            self.backbone, num_features = backbone
        else:
            self.backbone, num_features = self.backbones.get(backbone)(pretrained=pretrained, **backbone_kwargs)'''

        head = head(num_features, num_classes) if isinstance(head, FunctionType) else head
        self.head = head or nn.Conv2d(num_features, num_classes, kernel_size=1)

    def forward(self, x) -> torch.Tensor:
        x = self.backbone(x)
        return self.head(x)