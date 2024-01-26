#!/bin/bash

SRC_PATH='';
INSTALL_PATH='';
REPOSITORY='https://github.com/ton-blockchain/ton.git';
BRANCH='master';
CLEAN_FLAG=false;
LOG_FILE=$(readlink -f "./ton-build.log")
BUILD_THREADS=`expr \`cat /proc/cpuinfo | grep processor | wc -l\` - 1`
BUILD_CONFIG_FLAGS='-DCMAKE_BUILD_TYPE=Release'
BUILD_MAKE_FLAGS=''
BUILD_INSTALL_FLAGS='-DCMAKE_INSTALL_DO_STRIP=1'

usage() {
    BASENAME=$(basename "$0")
    echo 'Usage:';
    echo "    $BASENAME <parameters>";
    echo '';
    echo 'Required parameters:';
    echo '    -s  Source path, must be absolute!';
    echo '    -i  Install path, must be absolute!';
    echo '';
    echo 'Optional parameters:';
    echo '    -r  TON Repository URL';
    echo "        DEFAULT: $REPOSITORY";
    echo '    -b  Branch to checkout';
    echo "        DEFAULT: $BRANCH";
    echo '    -c  Clean: if specified, source path will be removed before work';
    echo '    -h  Show usage';
    echo 'Notes:';
    echo '    If source path already exists and clean flag is not set, this script will not';
    echo '    attempt to clone respository, instead it will checkout requested branch and perform pull';

    exit 1;
}

check_errs()
{
  # Function. Parameter 1 is the return code
  # Para. 2 is text to display on failure.
  if [ "${1}" -ne "0" ]; then
    echo "ERROR # ${1} : ${2}"
    # as a bonus, make our script exit with the right error code.
    exit ${1}
  fi
}

clean_path()
{
    IP=$(echo ${1} | tr -s /);
    echo ${IP%/}
}

check_path_absolute()
{
    if [[ "${1}" != /* ]]
    then
       echo "ERROR: Path ${1} is not absolute!"
       exit 1
    fi
}

print_line()
{
    echo "${1}"
    echo "${1}" >> $LOG_FILE
}

print_title()
{
    echo "" >> $LOG_FILE
    echo "------------------------------------------------------------------" >> $LOG_FILE
    print_line "${1}"
    echo "------------------------------------------------------------------" >> $LOG_FILE
    echo "" >> $LOG_FILE
}


while getopts ":s:i:r:b:ch" o; do
    case "${o}" in
        s)
            SRC_PATH=${OPTARG}
            ;;
        i)

            INSTALL_PATH=${OPTARG}
            ;;
        r)
            REPOSITORY=${OPTARG}
            ;;
        b)
            BRANCH=${OPTARG}
            ;;
        c)
            CLEAN_FLAG=true
            ;;
        *)
            usage
            ;;
    esac
done

SRC_PATH=$(clean_path $SRC_PATH)
INSTALL_PATH=$(clean_path $INSTALL_PATH)

if ([ -z ${SRC_PATH} ] || [ -z ${INSTALL_PATH} ]);
then
    usage;
fi

check_path_absolute $SRC_PATH
check_path_absolute $INSTALL_PATH

echo "Output of all commands can be found in file $LOG_FILE";
echo "" >$LOG_FILE

print_title "Process start"

if [ -d $SRC_PATH ] && [ "$CLEAN_FLAG" = true ];
then
    print_line "Deleting source path $SRC_PATH."
    rm -Rf $SRC_PATH
    check_errs $? "Removal of source path $SRC_PATH has failed"
fi

if [ ! -d $SRC_PATH ];
then
    print_title "Cloning repository $REPOSITORY into $SRC_PATH.";
    git clone --recursive $REPOSITORY $SRC_PATH >>$LOG_FILE 2>&1
    check_errs $? "Cloning of repository has failed, check logs"
fi

cd $SRC_PATH
print_line "Checking out branch $BRANCH.";
git checkout $BRANCH >>$LOG_FILE 2>&1
check_errs $? "Checkout of branch $BRANCH has failed, check logs"
git pull >>$LOG_FILE 2>&1
check_errs $? "Code pull has failed, check logs"
git submodule init >>$LOG_FILE 2>&1
git submodule update >>$LOG_FILE 2>&1
check_errs $? "Submodules update has failed, check logs"

if [ -d $SRC_PATH/build ];
then
    rm -Rf $SRC_PATH/build
    check_errs $? "Removal build path $SRC_PATH/build has failed"
fi

mkdir -p $SRC_PATH/build
check_errs $? "Creation of work / build path $SRC_PATH/build has failed"

print_title "Configuring build.";
cd $SRC_PATH/build
cmake $BUILD_CONFIG_FLAGS .. >>$LOG_FILE 2>&1
check_errs $? "Build configuration has failed, check logs"

print_title "Building.... this will take some time";
cd $SRC_PATH/build
make -j$BUILD_THREADS all .. >>$LOG_FILE 2>&1
check_errs $? "Build failed, check logs"

print_title "Installing into $INSTALL_PATH.";
cd $SRC_PATH/build
cmake $BUILD_BUILD_INSTALL_FLAGS -DCMAKE_INSTALL_PREFIX=$INSTALL_PATH -P cmake_install.cmake >>$LOG_FILE 2>&1
check_errs $? "Install failed, check logs"
cp dht/dht-ping-servers $INSTALL_PATH/bin
cp dht/dht-resolve $INSTALL_PATH/bin

print_line "Mission acomplished!"