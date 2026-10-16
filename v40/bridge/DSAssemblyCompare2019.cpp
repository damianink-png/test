// DS Compare V4.0 — ZW3D 2019 x64 native bridge.
// Uses only active model STEP export. NO Z3 open, close, save, or geometry calls.
// CAD operations are performed only on registered ZW3D command callbacks.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define PSAPI_VERSION 1
#include <windows.h>
#include <shellapi.h>
#include <psapi.h>
#include <cstring>
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

namespace {
HINSTANCE instance = nullptr;
using FnCmd = int (*)(const char*, void*, double);
using FnCmdUnload = int (*)(const char*);
using FnFileExport = int (*)(int, char*, void*);
using FnFileInqActive = void (*)(char*, int);
using FnRootInqActive = void (*)(char*, int);
FnCmd cmd = nullptr;
FnCmdUnload unloadCmd = nullptr;
FnFileExport exportStep = nullptr;
FnFileInqActive activeFile = nullptr;
FnRootInqActive activeRoot = nullptr;

// From ZW3D 2019 VxApi.h: svxSTEPData (byte AP, byte output, byte exportType,
// alignment padding, 32-bit EntCnt, 64-bit EntList on x64).
struct STEPData {
    char AppProtocol;
    char OutPut;
    char ExportType;
    int EntCnt;
    int* EntList;
};
static_assert(sizeof(STEPData) == 16, "ZW3D x64 STEPData ABI size mismatch");

std::wstring dirOf(const std::wstring& p) {
    const auto n = p.find_last_of(L"\\/");
    return n == std::wstring::npos ? std::wstring() : p.substr(0,n);
}
std::wstring exeDir() {
    wchar_t path[32768] = {};
    DWORD n = GetModuleFileNameW(instance, path, 32768);
    return n > 0 && n < 32768 ? dirOf(path) : L"";
}
std::wstring workDir() {
    wchar_t buf[MAX_PATH] = {};
    if (!GetTempPathW(MAX_PATH,buf)) return L"";
    std::wstring result = std::wstring(buf) + L"DSCompareV3";
    if (!CreateDirectoryW(result.c_str(),nullptr) && GetLastError() != ERROR_ALREADY_EXISTS) return L"";
    return result;
}
void logLine(const std::wstring& msg) {
    const std::wstring root = workDir();
    if (root.empty()) return;
    const std::wstring file = root + L"\\bridge.log";
    HANDLE h = CreateFileW(file.c_str(),FILE_APPEND_DATA,FILE_SHARE_READ | FILE_SHARE_WRITE,
                           nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(h==INVALID_HANDLE_VALUE) return;
    SYSTEMTIME tm;GetLocalTime(&tm);
    wchar_t prefix[80]={};
    swprintf_s(prefix,L"[%02d:%02d:%02d] ",tm.wHour,tm.wMinute,tm.wSecond);
    std::wstring line = std::wstring(prefix)+msg+L"\r\n";
    // Convert to UTF-8 to avoid locale dependent diagnostic messages.
    const int len = WideCharToMultiByte(CP_UTF8,0,line.c_str(),(int)line.size(),nullptr,0,nullptr,nullptr);
    if (len>0) {
        std::string bytes(size_t(len),'\0');
        WideCharToMultiByte(CP_UTF8,0,line.c_str(),(int)line.size(),&bytes[0],len,nullptr,nullptr);
        DWORD written=0; WriteFile(h,bytes.data(),DWORD(bytes.size()),&written,nullptr);
    }
    CloseHandle(h);
}
void notice(const wchar_t* msg,bool error=false) {
    MessageBoxW(nullptr,msg,L"DS Compare V4.0 — ZW3D Bridge",MB_OK | (error?MB_ICONERROR:MB_ICONINFORMATION));
}
void* apiSymbol(const char* name){
    // API symbols generally reside in host modules; walk loaded DLLs using PSAPI.
    HMODULE mods[2048] = {}; DWORD size=0;
    if (!EnumProcessModules(GetCurrentProcess(),mods,sizeof(mods),&size)) return nullptr;
    const size_t count=std::min<size_t>(2048,size / sizeof(HMODULE));
    for (size_t i=0;i<count;++i) if(mods[i]){
        FARPROC p=GetProcAddress(mods[i],name);
        if(p) return reinterpret_cast<void*>(p);
    }
    return nullptr;
}
template <typename T> void load(T& fn,const char* name) { fn=reinterpret_cast<T>(apiSymbol(name)); }
std::wstring toWide(const char* s) {
    if (!s || !*s) return L"";
    int n=MultiByteToWideChar(CP_ACP,0,s,-1,nullptr,0);
    if(n<=0)return L"";
    std::wstring w(size_t(n),L'\0');
    MultiByteToWideChar(CP_ACP,0,s,-1,&w[0],n);
    w.pop_back();return w;
}
std::string toAnsi(const std::wstring& w) {
    BOOL substitution=FALSE;
    if(w.empty()) return {};
    int n=WideCharToMultiByte(CP_ACP,WC_NO_BEST_FIT_CHARS,w.c_str(),-1,nullptr,0,nullptr,&substitution);
    if(n<=1 || substitution) return {};
    std::string a(size_t(n),'\0');
    WideCharToMultiByte(CP_ACP,WC_NO_BEST_FIT_CHARS,w.c_str(),-1,&a[0],n,nullptr,&substitution);
    if(substitution)return {};
    a.pop_back();return a;
}
std::wstring getFileFromMarker(wchar_t key) {
    std::wstring dir=workDir();
    if(dir.empty())return L"";
    std::wstring marker=dir+L"\\capture_"+std::wstring(1,key)+L".txt";
    std::wifstream file(marker);
    std::wstring path;
    if(!std::getline(file,path))return L"";
    if(path.empty() || GetFileAttributesW(path.c_str())==INVALID_FILE_ATTRIBUTES)return L"";
    return path;
}
bool writeMarker(wchar_t key, const std::wstring& path) {
    const std::wstring dir=workDir();
    if(dir.empty())return false;
    std::wofstream out(dir+L"\\capture_"+std::wstring(1,key)+L".txt",std::ios::trunc);
    if(!out)return false;
    out<<path<<L"\n";
    return bool(out);
}
std::wstring quoteArg(const std::wstring& text) {
    // Standard CreateProcess/CRT argv quoting including embedded quotes / slashes.
    std::wstring out=L"\"";size_t bs=0;
    for(wchar_t c:text){
        if(c==L'\\'){++bs;continue;}
        if(c==L'"'){out.append(bs*2+1,L'\\');out+=L'"';bs=0;continue;}
        out.append(bs,L'\\');bs=0;out+=c;
    }
    out.append(bs*2,L'\\');out+=L'"';return out;
}
std::wstring trim(const std::wstring& x) {
    const auto a=x.find_first_not_of(L" \r\n\t\""), b=x.find_last_not_of(L" \r\n\t\"");
    return a==std::wstring::npos?L"":x.substr(a,b-a+1);
}
std::wstring locateExe() {
    wchar_t env[32768]={};
    DWORD n=GetEnvironmentVariableW(L"DSCOMPARE_EXE",env,32768);
    if(n>0 && n<32768 && GetFileAttributesW(env)!=INVALID_FILE_ATTRIBUTES)return env;
    const std::wstring base=exeDir();
    const std::wstring a=base+L"\\DSCompareV3.exe";
    if(GetFileAttributesW(a.c_str())!=INVALID_FILE_ATTRIBUTES)return a;
    const std::wstring b=base+L"\\DSCompareV3\\DSCompareV3.exe";
    if(GetFileAttributesW(b.c_str())!=INVALID_FILE_ATTRIBUTES)return b;
    std::wifstream ini(base+L"\\DSComparePath.txt");
    std::wstring path;
    if(std::getline(ini,path)){
        path=trim(path);
        if(GetFileAttributesW(path.c_str())!=INVALID_FILE_ATTRIBUTES)return path;
    }
    return L"";
}
void launch(const std::wstring& a, const std::wstring& b) {
    const std::wstring exe=locateExe();
    if(exe.empty()){
        logLine(L"ERROR: executable not found alongside plugin DLL or in DSComparePath.txt");
        notice(L"Nie znaleziono DSCompareV3.exe.\n\nUmiesc folder programu obok DLL albo w folderze DLL zapisz plik DSComparePath.txt zawierajacy pelna sciezke do EXE.\n\nSzczegoly: %TEMP%\\DSCompareV3\\bridge.log",true);
        return;
    }
    std::wstring command=quoteArg(exe);
    if(!a.empty())command+=L" --a "+quoteArg(a);
    if(!b.empty())command+=L" --b "+quoteArg(b);
    const std::wstring cwd=dirOf(exe);
    STARTUPINFOW startup={};startup.cb=sizeof(startup);
    PROCESS_INFORMATION proc={};
    std::vector<wchar_t> mutableCmd(command.begin(),command.end());mutableCmd.push_back(L'\0');
    logLine(L"Starting standalone GUI with captured STEP models");
    BOOL ok=CreateProcessW(exe.c_str(),mutableCmd.data(),nullptr,nullptr,FALSE,
                            CREATE_NEW_PROCESS_GROUP,nullptr,cwd.c_str(),&startup,&proc);
    if(!ok){
        logLine(L"ERROR: CreateProcessW failed: "+std::to_wstring(GetLastError()));
        notice(L"Nie udalo sie uruchomic DSCompareV3.exe. Zobacz bridge.log.",true);
        return;
    }
    CloseHandle(proc.hThread); CloseHandle(proc.hProcess);
}
void exportCurrent(wchar_t key){
    // This function is called ONLY as ZW3D command callback. Never inside Win32 button handler.
    if(!exportStep || !activeFile){
        notice(L"ZW3D nie udostepnia cvxFileExport lub cvxFileInqActive.",true);return;
    }
    char fileName[1024]={};activeFile(fileName,(int)sizeof(fileName));
    char root[1024]={};if(activeRoot)activeRoot(root,(int)sizeof(root));
    if(!fileName[0]){notice(L"Otworz najpierw model Z3 i aktywuj wlasciwy obiekt (root) w ZW3D.",true);return;}
    std::wstring dir=workDir();
    if(dir.empty()){notice(L"Nie mozna utworzyc folderu roboczego w TEMP.",true);return;}
    SYSTEMTIME now;GetLocalTime(&now);
    wchar_t stamp[100]={};swprintf_s(stamp,L"%04d%02d%02d_%02d%02d%02d_%d",now.wYear,now.wMonth,now.wDay,now.wHour,now.wMinute,now.wSecond,GetCurrentProcessId());
    std::wstring step=dir+L"\\model_"+std::wstring(1,key)+L"_"+stamp+L".step";
    std::string apiPath=toAnsi(step);
    // vxPath is only 256 bytes in ZW3D 2019, so avoid silent truncation.
    if(apiPath.empty() || apiPath.size()>255){
        notice(L"Sciezka STEP jest za dluga lub nie jest reprezentowalna w kodowaniu ZW3D 2019. Zmien katalog TEMP.",true);return;
    }
    char buffer[256]={};memcpy(buffer,apiPath.c_str(),apiPath.size());
    STEPData options={1,1,0,0,nullptr}; // AP214 / assembly / all entities
    logLine(L"Export " + std::wstring(1,key) + L"; current Z3: " + toWide(fileName) + L"; root: " + toWide(root));
    const int result=exportStep(6,buffer,&options); // VX_EXPORT_TYPE_STEP == 6 in 2019 SDK
    if(result!=0 || GetFileAttributesW(step.c_str())==INVALID_FILE_ATTRIBUTES){
        logLine(L"ERROR: cvxFileExport returned " + std::to_wstring(result));
        notice(L"Eksport STEP z ZW3D nie powiodl sie. Zobacz bridge.log.\n\nOryginalny model nie zostal zapisany ani zamkniety.",true);return;
    }
    LARGE_INTEGER fileSize={};
    HANDLE h=CreateFileW(step.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(h!=INVALID_HANDLE_VALUE){GetFileSizeEx(h,&fileSize);CloseHandle(h);}
    if(fileSize.QuadPart<256){
        logLine(L"ERROR: STEP file unexpectedly small");
        notice(L"Eksport STEP jest pusty lub nieprawidlowy.",true);return;
    }
    if(!writeMarker(key,step)){
        logLine(L"ERROR: unable to write marker");
        notice(L"Eksport gotowy, ale nie zapisano wskazania pliku. Sprawdz prawa do TEMP.",true);return;
    }
    logLine(L"Export complete; STEP bytes: " + std::to_wstring(fileSize.QuadPart));
    if(key==L'A'){
        notice(L"Model A zostal wyeksportowany do STEP.\n\nOtworz i aktywuj teraz model B, a nastepnie wpisz ~DSCOMPARE_B.");
    }else{
        std::wstring a=getFileFromMarker(L'A');
        if(a.empty()){
            notice(L"Zapisano model B. Brakuje modelu A. Uzyj najpierw ~DSCOMPARE_A.",true);
        }else{
            launch(a,step);
        }
    }
}
void captureA(){exportCurrent(L'A');}
void captureB(){exportCurrent(L'B');}
void openGui(){launch(getFileFromMarker(L'A'),getFileFromMarker(L'B'));}
void usage(){notice(L"DS Compare V4.0\n\n~DSCOMPARE_A — eksport aktywnego modelu jako A\n~DSCOMPARE_B — eksport aktywnego modelu jako B i otwarcie analizy\n~DSCOMPARE — otwarcie osobnego programu\n\nAktywny dokument i root powinny byc prawidlowo ustawione przed eksportem.\n\nBez zapisu i zamykania dokumentow Z3.");}
} // namespace
BOOL WINAPI DllMain(HINSTANCE h,DWORD reason,LPVOID){
    if(reason==DLL_PROCESS_ATTACH){instance=h;DisableThreadLibraryCalls(h);}return TRUE;
}
extern "C" __declspec(dllexport) int DSAssemblyCompare2019Init(int,void*){
    load(cmd,"cvxCmdFunc");load(unloadCmd,"cvxCmdFuncUnload");
    load(exportStep,"cvxFileExport");load(activeFile,"cvxFileInqActive");load(activeRoot,"cvxRootInqActive");
    if(!cmd){logLine(L"ERROR: cvxCmdFunc missing");return 1;}
    // Keep ~DSAC for users migrating from V2.6; export commands have distinct names.
    int rc=0;
    rc|=cmd("DSAC",reinterpret_cast<void*>(&openGui),0);
    rc|=cmd("DSCOMPARE",reinterpret_cast<void*>(&openGui),0);
    rc|=cmd("DSCOMPARE_A",reinterpret_cast<void*>(&captureA),0);
    rc|=cmd("DSCOMPARE_B",reinterpret_cast<void*>(&captureB),0);
    rc|=cmd("DSCOMPARE_INFO",reinterpret_cast<void*>(&usage),0);
    logLine(L"DS Compare V4.0 plugin initialized; cvxFileExport="+std::to_wstring(exportStep!=nullptr));
    return rc?1:0;
}
extern "C" __declspec(dllexport) int DSAssemblyCompare2019Exit(){
    if(unloadCmd){
        unloadCmd("DSAC");unloadCmd("DSCOMPARE");unloadCmd("DSCOMPARE_A");
        unloadCmd("DSCOMPARE_B");unloadCmd("DSCOMPARE_INFO");
    }
    logLine(L"DS Compare V4.0 plugin unloaded");
    return 0;
}
