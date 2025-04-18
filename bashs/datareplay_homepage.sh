
recorder=syhlab
exp_name=test_record
exp_num=20250411_185907

cd ..
python lerobot/scripts/visualize_dataset_html.py \
  --repo-id=${recorder}/${exp_name}_${exp_num}  \
