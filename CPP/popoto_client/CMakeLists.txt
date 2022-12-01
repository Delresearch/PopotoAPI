cmake_minimum_required(VERSION 3.10)

# set the project name
project(popoto_play_rec_test)
add_compile_options("-g")
# build the API library
add_library(popoto_api  STATIC src/popoto_client.cpp src/TCPClient.cpp)

# add the executable
add_executable(popoto_play_rec_test  Example/play_rec_test.cpp Example/play_record_utils.cpp )

# set include path
target_include_directories(popoto_play_rec_test PRIVATE include)
target_include_directories(popoto_api PRIVATE include)


# add libraries needed (pthread math and stdc++)
target_link_libraries(popoto_play_rec_test m stdc++ pthread popoto_api)


# add the executable
add_executable(popoto_play  Example/playpcm.cpp Example/play_record_utils.cpp  )
target_include_directories(popoto_play PRIVATE include)

# add libraries needed (pthread math and stdc++)
target_link_libraries(popoto_play m stdc++ pthread popoto_api)


# add the executable
add_executable(popoto_record  Example/recordpcm.cpp Example/play_record_utils.cpp  )
target_include_directories(popoto_record PRIVATE include)

# add libraries needed (pthread math and stdc++)
target_link_libraries(popoto_record m stdc++ pthread popoto_api)
