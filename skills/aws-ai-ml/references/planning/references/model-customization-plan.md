# End-to-End Model Customization Plan

**Recommended for:** users who are certain they want to finetune a model, and users who clearly communicate that they want to finetune a model

1. **Define Use Case** - Capture the business problem, users, and success criteria. *(Skill: use-case-specification)*
2. **Select Base Model** - Choose a base model from SageMaker Hub based on benchmarks and use case fit. *(Skill: model-selection)*
3. **Verify Environment** - Check SDK version, region, and execution role are configured. *(Skill: sdk-getting-started)*
4. **Select Finetuning Technique** - Choose a fine-tuning technique and validate compatibility with the selected model. *(Skill: finetuning-technique)*
5. **Evaluate Dataset** - Assess data quality, completeness, and format. *(Skill: dataset-evaluation)*
6. **Transform Dataset** - Convert the dataset to the required format for the selected fine-tuning technique and base model. *(Skill: dataset-transformation)*
7. **Fine-Tune Model** - Train a custom model using SageMaker. *(Skill: finetuning)*
8. **Evaluate Model** - Measure model performance against success criteria. *(Skill: model-evaluation)*
9. **Deploy Model** - Create an endpoint for inference. *(Skill: model-deployment)*

**Note:** This skill does not have a validated workflow for synthetic data generation. If the user asks about generating training data, let them know you can help with general guidance but it is not a tested workflow in this skill.
