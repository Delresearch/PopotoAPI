#!/bin/bash


# if we don't have a build directory,   make one

if [ ! -d "build" ]; then
mkdir build
fi

cd build
cmake ..
make

