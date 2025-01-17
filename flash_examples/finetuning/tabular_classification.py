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
from torchmetrics.classification import Accuracy, Precision, Recall

import flash
from flash.data.utils import download_data
from flash.tabular import TabularClassifier, TabularData

# 1. Download the data
download_data("https://pl-flash-data.s3.amazonaws.com/titanic.zip", "data/")

# 2. Load the data
datamodule = TabularData.from_csv(
    target_col="Survived",
    train_csv="./data/titanic/titanic.csv",
    test_csv="./data/titanic/test.csv",
    categorical_cols=["Sex", "Age", "SibSp", "Parch", "Ticket", "Cabin", "Embarked"],
    numerical_cols=["Fare"],
    val_size=0.25,
)

# 3. Build the model
model = TabularClassifier.from_data(datamodule, metrics=[Accuracy(), Precision(), Recall()])

# 4. Create the trainer
trainer = flash.Trainer(fast_dev_run=True)

# 5. Train the model
trainer.fit(model, datamodule=datamodule)

# 6. Test model
trainer.test(model)

# 7. Save it!
trainer.save_checkpoint("tabular_classification_model.pt")
