
recorder=syhlab
exp_name=justmove
exp_num=20250421_154412

cd ..
python lerobot/scripts/visualize_dataset_html.py \
  --repo-id=${recorder}/${exp_name}_${exp_num}  \
