datetime=`date '+%Y%m%d_%H%M%S'`
model=$1
tag=$2
log_file=$1_coco_log_${datetime}_$2.txt
GPUS_PER_NODE=8 ./tools/run_dist_launch.sh 8 ./configs/$1_deformable_detr_plus_iterative_bbox_refinement_plus_plus_two_stage.sh > ${log_file} 2>&1 &
sleep 2
tail -f ${log_file}

