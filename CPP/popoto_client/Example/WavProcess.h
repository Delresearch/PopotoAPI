/**
 * @file wavProcess.h
 * @author Aaron
 * @date 2021-09-01
 */

#ifndef WAVPROCESS_H
#define WAVPROCESS_H
#include <iostream>
#include <fstream>
#include <vector>
#include <ctime>
#include <chrono>


class WavProcess {
    private: 
        struct Header
        {
            char riff[5] = "RIFF";
            uint32_t header_remaining_size = 50;
            char wave[5] = "WAVE";
            char fmt_[5] = "fmt ";
            uint32_t format_len = 18;
            uint16_t format = 3;
            uint16_t channel_num = 1;
            uint32_t sample_rate = 102400;
            uint32_t byte_rate = 409600;
            uint16_t block_align = 4;
            uint16_t bits_per_sample = 32;

            uint16_t cb_size = 0;

            char fact[5] = "fact";
            uint32_t fact_chunk_size = 4;
            uint32_t dw_sample_length = sample_rate;

            char data_header[5] = "data";
            uint32_t data_size = 0;
        };

        bool _test_header_val(char * name, char * var, char * expected_val){
            if (strlen(var) != strlen(expected_val)) {
                std::cout << "(WAV file header analysis): Mismatched strings: Strings '" << var << "' and '" << expected_val << "' should be the same size." << std::endl;
                return true;
            }
            for (uint32_t i=0; i<strlen(var); i++) {
                if (var[i] != expected_val[i]) {
                    std::cout << "byte " << i << " of " << strlen(var) << " (WAV file header analysis): '" << name << "' should be '" << expected_val << "', but instad is '" << var << "'." << std::endl;
                    return true;
                }
            }
            return false;
        }
        bool _test_header_val(char * name, uint16_t var, uint16_t expected_val){
            if (var != expected_val) {
                std::cout << "(WAV file header analysis): '" << name << "' should be '" << expected_val << "', but instad is '" << var << "'." << std::endl;
                return true;
            }
            return false;
        }
        bool _test_header_val(char * name, uint32_t var, uint32_t expected_val){
                if (var != expected_val) {
                std::cout << "(WAV file header analysis): '" << name << "' should be '" << expected_val << "', but instad is '" << var << "'." << std::endl;
                return true;
            }
            return false;
        }

        int _test_header(Header h){
            return (
                (_test_header_val((char*)"filetype (bytes 0-3)"         , h.riff, (char*)"RIFF") << 8) +
                (_test_header_val((char*)"file-format (bytes 8-11)"     , h.wave, (char*)"WAVE") << 7) +
                (_test_header_val((char*)"fmt (bytes 12-15)"            , h.fmt_, (char*)"fmt ") << 6) +
                (_test_header_val((char*)"format (bytes 20-21)"         , h.format, 3)           << 5) + //32-bit float
                (_test_header_val((char*)"channels (bytes 22-23)"       , h.channel_num, 1)      << 4) +
                (_test_header_val((char*)"samplerate (bytes 24-27)"     , h.sample_rate, 102400) << 3) +
                (_test_header_val((char*)"byterate (bytes 28-31)"       , h.byte_rate, 409600)  << 2) +
                (_test_header_val((char*)"block-align (bytes 32-33)"    , h.block_align, 4)      << 1) +
                _test_header_val((char*)"bits-per-sample (bytes 34-35)" , h.bits_per_sample, 32)
            );
        }
    public:
        std::pair<int, int> getSampleData(FILE * wavptr){
        	if (wavptr == NULL) {
        		throw "File path incorrect";
        	}

            Header header;
            std::fseek(wavptr, 0, SEEK_SET);

            header.riff[4] = 0;
            std::fread(&header.riff, 1, 4, wavptr);
            std::fread(&header.header_remaining_size, 1, 4, wavptr);
            header.wave[4] = 0;
            std::fread(&header.wave, 1, 4, wavptr);
            header.fmt_[4] = 0;
            std::fread(&header.fmt_, 1, 4, wavptr);
            std::fread(&header.format_len, 1, 4, wavptr);
            std::fread(&header.format, 1, 2, wavptr);
            std::fread(&header.channel_num, 1, 2, wavptr);
            std::fread(&header.sample_rate, 1, 4, wavptr);
            std::fread(&header.byte_rate, 1, 4, wavptr);
            std::fread(&header.block_align, 1, 2, wavptr);
            std::fread(&header.bits_per_sample, 1, 2, wavptr);
            header.data_header[4] = 0;
            std::fread(&header.data_header, 1, 4, wavptr);

            int error = _test_header(header);
            if (error){
            	throw error;
            }

            char step = 0;
            while (step <= 3){
                char this_byte = 0;
                std::fread(&this_byte, 1, 1, wavptr);
                switch (this_byte) {
                    case 'd':
                        step = 1;
                        break;
                    case 'a':
                        if (step == 1 || step == 3) {
                            step++;
                        }
                        break;
                    case 't':
                        if (step == 2) {
                            step = 3;
                        }
                        break;
                }
            }

            std::fread(&header.data_size, 4, 1, wavptr);

            int header_size = std::ftell(wavptr);

            return std::make_pair(header_size, header.data_size);
        }
        void generateHeader(FILE * wavptr){
            if (wavptr == NULL) {
        		throw "File path incorrect";
        	}
            Header header;
            fseek(wavptr, 0, SEEK_SET);
            fwrite(&header.riff                  , 4, 1, wavptr);
            fwrite(&header.header_remaining_size , 4, 1, wavptr);
            fwrite(&header.wave                  , 4, 1, wavptr);
            fwrite(&header.fmt_                  , 4, 1, wavptr);
            fwrite(&header.format_len            , 4, 1, wavptr);
            fwrite(&header.format                , 2, 1, wavptr);
            fwrite(&header.channel_num           , 2, 1, wavptr);
            fwrite(&header.sample_rate           , 4, 1, wavptr);
            fwrite(&header.byte_rate             , 4, 1, wavptr);
            fwrite(&header.block_align           , 2, 1, wavptr);
            fwrite(&header.bits_per_sample       , 2, 1, wavptr);
            fwrite(&header.cb_size               , 2, 1, wavptr);
            fwrite(&header.fact                  , 4, 1, wavptr);
            fwrite(&header.fact_chunk_size       , 4, 1, wavptr);
            fwrite(&header.dw_sample_length      , 4, 1, wavptr);
            fwrite(&header.data_header           , 4, 1, wavptr);
            fwrite(&header.data_size             , 4, 1, wavptr);
        }
};
#endif
