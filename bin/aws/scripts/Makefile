CLK =? A0

all:
	aws-gen-build
	cd build/scripts && ./aws_build_dcp_from_cl.sh -clock_recipe_a $CLK
	tail -f `find . -name "*.log"`
fg:
	aws-gen-build
	cd build/scripts && ./aws_build_dcp_from_cl.sh -clock_recipe_a $CLK -foreground

help:
	@echo "make [all|fg|help] [CLK=[A0|A1|A2]] "
