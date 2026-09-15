#include "renegade_audio_output_buffers.h"
#include <algorithm>
#include <atomic>
#include <cassert>
#include <cstdio>
#include <vector>
#include <pthread.h>
constexpr int kAudioFramesPerBuffer=1024, kAudioChannels=2;
constexpr size_t kAudioStartupSamples=12288;
pthread_mutex_t g_audio_mutex=PTHREAD_MUTEX_INITIALIZER;
std::vector<int16_t> g_audio_ring;
size_t g_audio_read=0, g_audio_write=0, g_audio_count=0;
bool g_audio_enabled=true, g_audio_drop_logged=false, g_audio_thread_running=true;
bool g_audio_thread_entry_logged=false, g_audio_first_output_logged=false;
int g_audio_port=7;
const char *g_movie_name="generated";
std::atomic<bool> g_audio_stop(false), g_audio_drained(false), g_audio_decode_eof(true);
std::atomic<int64_t> g_presentation_start_us(1);
std::atomic<uint64_t> g_audio_wait_count(0), g_audio_output_buffers(0);
std::atomic<uint64_t> g_audio_output_samples(0), g_audio_partial_output_buffers(0);
std::atomic<uint64_t> g_audio_high_water_samples(0), g_audio_nonzero_samples(0);
std::atomic<unsigned> g_audio_peak(0);
void A30_Vita_Log(const char *,...) {}
void sceKernelDelayThread(unsigned) { assert(false && "fixture must not starve"); }
bool Start_Audio_Output_Thread() { return true; }
const int16_t *pending=nullptr;
std::vector<int16_t> pending_copy, consumed;
bool drained=false;
int sceAudioOutOutput(int port,const void *pointer) {
    assert(port==7);
    if (pending) {
        assert(std::equal(pending_copy.begin(),pending_copy.end(),pending));
        consumed.insert(consumed.end(),pending_copy.begin(),pending_copy.end());
    }
    pending=static_cast<const int16_t *>(pointer);
    if (pending) {
        assert(reinterpret_cast<uintptr_t>(pointer)%64==0);
        pending_copy.assign(pending,pending+2048);
    } else drained=true;
    return 1024; // Success is nonnegative, not necessarily zero.
}
#include "bink-audio-production.inc"
int main() {
    // Both producer and consumer wrap; final hardware block is partial/padded.
    for (size_t offset : {0U,1U,2047U,6999U}) {
        g_audio_ring.assign(7000,0);
        g_audio_read=g_audio_write=offset; g_audio_count=0;
        consumed.clear(); pending=nullptr; drained=false;
        std::vector<int16_t> input(6147);
        for (size_t i=0;i<input.size();++i) input[i]=int16_t(i%60000-30000);
        Queue_Audio(input.data(),3100);
        Queue_Audio(input.data()+3100,input.size()-3100);
        assert(g_audio_count==input.size());
        Audio_Output_Thread(nullptr);
        assert(drained && pending==nullptr && g_audio_count==0);
        assert(consumed.size()==8192);
        assert(std::equal(input.begin(),input.end(),consumed.begin()));
        for (size_t i=input.size();i<consumed.size();++i) assert(consumed[i]==0);
    }
    std::puts("native audio lifetime and wrapped PCM transfer PASS");
}
