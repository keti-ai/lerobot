
recorder=syhlab
#EXP_NAME=justmove
#EXP_NUM=20250421_154412

EXP_NAME=move_aroundT
EXP_NUM=20250421_162801
REPO_ID=syhlab/${EXP_NAME}_${EXP_NUM}

cd ..
python lerobot/scripts/visualize_dataset_html.py \
  --repo-id=syhlab/move_aroundT_20250421_162801 \
  --host 10.252.205.103 \
  --port 9090
