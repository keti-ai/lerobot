# 250418 datacollect scripts for push t syh
export recorder=syhlab
export exp_name=pusht
export exp_num=$(date +"%Y%m%d_%H%M%S")

python scripts/train.py \
--policy.type=pi0 \
--env.type=pusht \
--train.dataset.repo_id=syhlab/pusht_${exp_num} \
--train.num_epochs=100 \
--train.batch_size=64 \
--policy.device=cuda \
--wandb.enable=true \
--policy.prompt="push the green T into the black T outline"
