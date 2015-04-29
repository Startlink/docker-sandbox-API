#!/bin/sh
while [ "$1" = "-o" ] || [ "$1" = "-v" ];
do
	if [ "$1" = "-o" ]
	then
		shift
		name=$1
		shift
	elif [ "$1" = "-v" ]
	then
		shift
		volume=$1
		shift
	fi
done

if [ "$name" = "" ]
then
	name="a.out"
fi

argv=""
for filename in $@
do
	argv="$argv /data/$filename";
done

if [ "$volume" = "" ]
then
	COMPILE=$(docker run -i -a stdin cpp g++ -o /data/$name $argv)
else
	COMPILE=$(docker run -i -a stdin -v $volume cpp g++ -o /data/$name $argv)
fi

docker logs $COMPILE

