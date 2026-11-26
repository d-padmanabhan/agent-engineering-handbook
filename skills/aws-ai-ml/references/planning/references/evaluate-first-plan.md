# Evaluate-First Plan

**Recommended for:** Users who want to check if finetuning is necessary to solving their problem, users who want to check which base model is best for their use case, users who don't want to commit to finetuning yet, and users who are open to suggestions

1. **Define Use Case** - Capture the business problem, users, and success criteria. *(Skill: use-case-specification)*
2. **Select Base Model** - Choose a base model from SageMaker Hub. *(Skill: model-selection)*
3. **Verify Environment** - Check SDK version, region, and execution role are configured. *(Skill: sdk-getting-started)*
4. **Evaluate Dataset** - Validate the evaluation dataset (query/response format). *(Skill: dataset-evaluation)*
5. **Transform Dataset** - Convert to SageMaker evaluation format if needed. *(Skill: dataset-transformation)*
6. **Evaluate Model** - Run the base model against the evaluation dataset and present results against success criteria. *(Skill: model-evaluation)*
7. **Decision Gate** - Present evaluation results. User decides whether to fine-tune or stop.

If the user decides to fine-tune after the decision gate, extend the plan:

<!-- markdownlint-disable MD029 -->

8. **Select Finetuning Technique** - Choose the appropriate finetuning technique. *(Skill: finetuning-technique)*
9. **Evaluate Training Dataset** - Validate training data format. *(Skill: dataset-evaluation)*
10. **Transform Training Dataset** - Convert to training format. *(Skill: dataset-transformation)*
11. **Fine-Tune Model** - Train the model. *(Skill: finetuning)*
12. **Evaluate Finetuned Model** - Compare against base model results. *(Skill: model-evaluation)*
13. **Deploy Model** - Create an endpoint. *(Skill: model-deployment)*

<!-- markdownlint-enable MD029 -->

At the decision gate, present data objectively against the user's success criteria. Do not recommend - let the user decide.
