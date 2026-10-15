// DS Compare V3.0 experimental bridge, ZW3D 2019 x64.
// Only exports the active document as STEP; B-Rep runs out-of-process.
// NEVER opens/closes/saves Z3 or invokes ZW3D CAD API from a Win32 UI callback.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define PSAPI_VERSION 1
#include <windows.h>
#include <psapi.h>
#include <string>
#include <vector>
#include <fstream>
#include <algorithm>
#include <cstring>
#include <cstdio>

namespace {
HINSTANCE self = nullptr;
using Cmd = int (*)(const char*,void*,double);
using Unload = int (*)(const char*);
using Export = int (*)(int,char*,void*);
using Active = void (*)(char*,int);
Cmd addCommand=nullptr;Unload unload=nullptr;Export stepExport=nullptr;Active currentFile=nullptr;
struct STEPData { char AppProtocol; char OutPut; char ExportType; int EntCnt; int* EntList; };
static_assert(sizeof(STEPData)==16,"ZW3D 2019 x64 STEP ABI mismatch");

std::wstring dirname(const std::wstring& p){
    auto x=p.find_last_of(L"\\/");return x==std::wstring::npos?L"":p.substr(0,x);
}
std::wstring dllFolder(){
    wchar_t path[32768]={};DWORD n=GetModuleFileNameW(self,path,32768);
    return n>0&&n<32768?dirname(path):L"";
}
std::wstring tmpFolder(){
    wchar_t tmp[MAX_PATH]={};if(!GetTempPathW(MAX_PATH,tmp))return L"";
    std::wstring path=std::wstring(tmp)+L"DSCompareV3";
    if(!CreateDirectoryW(path.c_str(),nullptr)&&GetLastError()!=ERROR_ALREADY_EXISTS)return L"";
    return path;
}
void trace(const wchar_t* what,int val=0){
    std::wstring d=tmpFolder();if(d.empty())return;
    HANDLE h=CreateFileW((d+L"\\bridge.log").c_str(),FILE_APPEND_DATA,FILE_SHARE_READ,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(h==INVALID_HANDLE_VALUE)return;
    SYSTEMTIME t;GetLocalTime(&t);char buffer[400];
    int n=sprintf_s(buffer,"[%02u:%02u:%02u] %ls (%d)\r\n",t.wHour,t.wMinute,t.wSecond,what,val);
    if(n>0){DWORD done=0;WriteFile(h,buffer,DWORD(n),&done,nullptr);}CloseHandle(h);
}
void alert(const wchar_t* m,bool err=false){MessageBoxW(nullptr,m,L"DS Compare V3.0",MB_OK|(err?MB_ICONERROR:MB_ICONINFORMATION));}
void* symbol(const char* name){
    HMODULE mods[2048]={};DWORD len=0;
    if(!EnumProcessModules(GetCurrentProcess(),mods,sizeof(mods),&len))return nullptr;
    for(unsigned i=0;i<std::min<unsigned>(2048,len/sizeof(HMODULE));++i){
        auto p=GetProcAddress(mods[i],name);if(p)return reinterpret_cast<void*>(p);
    }return nullptr;
}
template<class T> void bind(T& fn,const char* name){fn=reinterpret_cast<T>(symbol(name));}
std::wstring getExe(){
    wchar_t env[32768]={};DWORD len=GetEnvironmentVariableW(L"DSCOMPARE_EXE",env,32768);
    if(len>0&&len<32768&&GetFileAttributesW(env)!=INVALID_FILE_ATTRIBUTES)return env;
    std::wstring folder=dllFolder();std::wstring exe=folder+L"\\DSCompareV3.exe";
    if(GetFileAttributesW(exe.c_str())!=INVALID_FILE_ATTRIBUTES)return exe;
    std::wifstream file(folder+L"\\DSComparePath.txt");std::wstring candidate;
    if(std::getline(file,candidate)){
        if(!candidate.empty()&&candidate.front()==0xfeff)candidate.erase(0,1);
        if(candidate.size()>1&&candidate.front()==L'"'&&candidate.back()==L'"')candidate=candidate.substr(1,candidate.size()-2);
        if(GetFileAttributesW(candidate.c_str())!=INVALID_FILE_ATTRIBUTES)return candidate;
    }
    return L"";
}
std::wstring marker(wchar_t x){return tmpFolder()+L"\\model_"+std::wstring(1,x)+L".path";}
void setMarker(wchar_t x,const std::wstring& value){
    std::wofstream f(marker(x),std::ios::trunc);if(f)f<<value<<L"\n";
}
std::wstring getMarker(wchar_t x){
    std::wifstream f(marker(x));std::wstring p;
    if(std::getline(f,p)&&GetFileAttributesW(p.c_str())!=INVALID_FILE_ATTRIBUTES)return p;
    return L"";
}
std::wstring quoted(const std::wstring& val){
    std::wstring o=L"\"";unsigned bs=0;
    for(wchar_t c:val){
        if(c==L'\\'){++bs;continue;}
        if(c==L'"'){o.append(bs*2+1,L'\\');o+=c;bs=0;continue;}
        o.append(bs,L'\\');bs=0;o+=c;
    }
    o.append(bs*2,L'\\');return o+L"\"";
}
void launch(const std::wstring& a,const std::wstring& b){
    std::wstring exe=getExe();
    if(exe.empty()){
        alert(L"Nie znaleziono DSCompareV3.exe.\nUmiesc EXE obok DLL lub utworz DSComparePath.txt z pelna sciezka do EXE.",true);return;
    }
    std::wstring cmd=quoted(exe);
    if(!a.empty())cmd+=L" --a "+quoted(a);
    if(!b.empty())cmd+=L" --b "+quoted(b);
    std::vector<wchar_t> arg(cmd.begin(),cmd.end());arg.push_back(0);
    STARTUPINFOW si={};si.cb=sizeof(si);PROCESS_INFORMATION pi={};
    BOOL ok=CreateProcessW(exe.c_str(),arg.data(),nullptr,nullptr,FALSE,
                            CREATE_NEW_PROCESS_GROUP,nullptr,dirname(exe).c_str(),&si,&pi);
    if(!ok){trace(L"CreateProcess failed",GetLastError());alert(L"Nie mozna uruchomic DSCompareV3.exe. Zobacz %TEMP%\\DSCompareV3\\bridge.log.",true);return;}
    CloseHandle(pi.hThread);CloseHandle(pi.hProcess);trace(L"GUI launched");
}
void capture(wchar_t tag){
    // Executed ONLY as registered CAD command.
    if(!stepExport||!currentFile){alert(L"ZW3D 2019 nie udostepnia funkcji eksportu STEP.",true);return;}
    char active[1024]={};currentFile(active,1024);
    if(!active[0]){alert(L"Najpierw aktywuj wlasciwy model Z3 w ZW3D.",true);return;}
    std::wstring dir=tmpFolder();if(dir.empty()){alert(L"Nie mozna utworzyc katalogu TEMP.",true);return;}
    SYSTEMTIME t;GetLocalTime(&t);wchar_t suffix[90]={};
    swprintf_s(suffix,L"%04u%02u%02u_%02u%02u%02u_%lu",t.wYear,t.wMonth,t.wDay,t.wHour,t.wMinute,t.wSecond,GetCurrentProcessId());
    std::wstring path=dir+L"\\capture_"+tag+L"_"+suffix+L".step";
    BOOL replaced=FALSE;
    int length=WideCharToMultiByte(CP_ACP,WC_NO_BEST_FIT_CHARS,path.c_str(),-1,nullptr,0,nullptr,&replaced);
    if(length<=1||length>256||replaced){alert(L"Sciezka eksportu STEP jest zbyt dluga lub niezgodna z kodowaniem ZW3D.",true);return;}
    char filePath[256]={};
    if(!WideCharToMultiByte(CP_ACP,WC_NO_BEST_FIT_CHARS,path.c_str(),-1,filePath,256,nullptr,&replaced)||replaced)return;
    STEPData options={1,1,0,0,nullptr}; // AP214, assembly, all entities. enum VX_EXPORT_TYPE_STEP = 6.
    trace(L"Export begin");
    int rc=stepExport(6,filePath,&options);
    if(rc!=0||GetFileAttributesW(path.c_str())==INVALID_FILE_ATTRIBUTES){
        trace(L"cvxFileExport failed",rc);alert(L"Eksport STEP nie powiodl sie. Zobacz bridge.log.",true);return;
    }
    LARGE_INTEGER size={};HANDLE h=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(h!=INVALID_HANDLE_VALUE){GetFileSizeEx(h,&size);CloseHandle(h);}
    if(size.QuadPart<256){alert(L"Plik STEP jest nieprawidlowy lub pusty.",true);return;}
    setMarker(tag,path);trace(L"Export completed",rc);
    if(tag==L'A')alert(L"Model A wyeksportowany.\nTeraz aktywuj model B i wpisz ~DSCOMPARE_B.");
    else{
        std::wstring a=getMarker(L'A');
        if(a.empty())alert(L"Brak modelu A. Najpierw wpisz ~DSCOMPARE_A.",true);
        else launch(a,path);
    }
}
void cA(){capture(L'A');}void cB(){capture(L'B');}
void cOpen(){launch(getMarker(L'A'),getMarker(L'B'));}
} // namespace

BOOL WINAPI DllMain(HINSTANCE h,DWORD reason,LPVOID){
    if(reason==DLL_PROCESS_ATTACH){self=h;DisableThreadLibraryCalls(h);}return TRUE;
}
extern "C" __declspec(dllexport) int DSAssemblyCompare2019Init(int,void*){
    bind(addCommand,"cvxCmdFunc");bind(unload,"cvxCmdFuncUnload");
    bind(stepExport,"cvxFileExport");bind(currentFile,"cvxFileInqActive");
    if(!addCommand){trace(L"cvxCmdFunc missing");return 1;}
    int rc=0;rc|=addCommand("DSAC",reinterpret_cast<void*>(&cOpen),0);
    rc|=addCommand("DSCOMPARE",reinterpret_cast<void*>(&cOpen),0);
    rc|=addCommand("DSCOMPARE_A",reinterpret_cast<void*>(&cA),0);
    rc|=addCommand("DSCOMPARE_B",reinterpret_cast<void*>(&cB),0);
    trace(L"DS Compare V3 plugin loaded",rc);return rc?1:0;
}
extern "C" __declspec(dllexport) int DSAssemblyCompare2019Exit(){
    if(unload){unload("DSAC");unload("DSCOMPARE");unload("DSCOMPARE_A");unload("DSCOMPARE_B");}
    trace(L"DS Compare V3 plugin unloaded");return 0;
}
