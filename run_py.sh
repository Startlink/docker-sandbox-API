#!/bin/sh
stdin="stdin.txt"
volumn=""
memoryLimit=128
strictMemory=0
while [ "$1" = "--stdin" ] || [ "$1" = "-v" ] || [ "$1" = "-m" ] || [ "$1" = "--strict" ];
do
	if [ "$1" = "--stdin" ]
	then
		shift
		stdin=$1
		shift
	elif [ "$1" = "-v" ]
	then
		shift
		volume=$1
		shift
	elif [ "$1" = "-m" ]
	then
		shift
		memoryLimit=$1
		shift
	elif [ "$1" = "--strict" ]
	then
		shift
		strictMemory=1
	fi
done

if [ $strictMemory = 0 ]
then
	swapLimit=$(($memoryLimit * 2))
	OUTPUT=$(cat $stdin | docker run -i -a stdin --net none --memory "$memoryLimit"m --memory-swap "$swapLimit"m -v $volume cpp $*)
else
	OUTPUT=$(cat $stdin | docker run -i -a stdin --net none --memory "$memoryLimit"m --memory-swap "$memoryLimit"m -v $volume cpp $*)
fi

docker logs $OUTPUT

docker stop $OUTPUT > /dev/null
docker rm $OUTPUT > /dev/null
