ps -x |grep agent  | awk -F' ' '{print $1}' |xargs kill -9
