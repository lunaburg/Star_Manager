
//  Microsoft (R) .NET Framework IL Disassembler.  Version 4.8.3928.0



// 警告 : 这是一个不完整的反汇编程序，不适合于重新汇编



.class public auto ansi beforefieldinit Studio.Info
       extends class [IL]Singleton`1<class Studio.Info>
{
  .class auto ansi nested public beforefieldinit FileInfo
         extends [mscorlib]System.Object
  {
    .field public string manifest
    .field public string bundlePath
    .field public string fileName
    .method public hidebysig specialname 
            instance bool  get_Check() cil managed
    {
      // 代码大小       30 (0x1e)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      string Studio.Info/FileInfo::bundlePath
      IL_0006:  call       bool [IL]NullCheck::IsNullOrEmpty(string)
      IL_000b:  ldc.i4.0
      IL_000c:  ceq
      IL_000e:  ldarg.0
      IL_000f:  ldfld      string Studio.Info/FileInfo::fileName
      IL_0014:  call       bool [IL]NullCheck::IsNullOrEmpty(string)
      IL_0019:  ldc.i4.0
      IL_001a:  ceq
      IL_001c:  and
      IL_001d:  ret
    } // end of method FileInfo::get_Check

    .method public hidebysig instance void 
            Clear() cil managed
    {
      // 代码大小       34 (0x22)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldstr      ""
      IL_0006:  stfld      string Studio.Info/FileInfo::manifest
      IL_000b:  ldarg.0
      IL_000c:  ldstr      ""
      IL_0011:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_0016:  ldarg.0
      IL_0017:  ldstr      ""
      IL_001c:  stfld      string Studio.Info/FileInfo::fileName
      IL_0021:  ret
    } // end of method FileInfo::Clear

    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       40 (0x28)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldstr      ""
      IL_0006:  stfld      string Studio.Info/FileInfo::manifest
      IL_000b:  ldarg.0
      IL_000c:  ldstr      ""
      IL_0011:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_0016:  ldarg.0
      IL_0017:  ldstr      ""
      IL_001c:  stfld      string Studio.Info/FileInfo::fileName
      IL_0021:  ldarg.0
      IL_0022:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0027:  ret
    } // end of method FileInfo::.ctor

    .property instance bool Check()
    {
      .get instance bool Studio.Info/FileInfo::get_Check()
    } // end of property FileInfo::Check
  } // end of class FileInfo

  .class auto ansi nested public beforefieldinit LoadCommonInfo
         extends Studio.Info/FileInfo
  {
    .field public string name
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       18 (0x12)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldstr      ""
      IL_0006:  stfld      string Studio.Info/LoadCommonInfo::name
      IL_000b:  ldarg.0
      IL_000c:  call       instance void Studio.Info/FileInfo::.ctor()
      IL_0011:  ret
    } // end of method LoadCommonInfo::.ctor

  } // end of class LoadCommonInfo

  .class auto ansi nested public beforefieldinit CategoryInfo
         extends [mscorlib]System.Object
  {
    .field public int32 sort
    .field public string name
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       18 (0x12)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldstr      ""
      IL_0006:  stfld      string Studio.Info/CategoryInfo::name
      IL_000b:  ldarg.0
      IL_000c:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0011:  ret
    } // end of method CategoryInfo::.ctor

  } // end of class CategoryInfo

  .class auto ansi nested public beforefieldinit GroupInfo
         extends [mscorlib]System.Object
  {
    .field public int32 sort
    .field public string name
    .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/CategoryInfo> dicCategory
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       29 (0x1d)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldstr      ""
      IL_0006:  stfld      string Studio.Info/GroupInfo::name
      IL_000b:  ldarg.0
      IL_000c:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/CategoryInfo>::.ctor()
      IL_0011:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/CategoryInfo> Studio.Info/GroupInfo::dicCategory
      IL_0016:  ldarg.0
      IL_0017:  call       instance void [mscorlib]System.Object::.ctor()
      IL_001c:  ret
    } // end of method GroupInfo::.ctor

  } // end of class GroupInfo

  .class auto ansi nested public beforefieldinit BoneInfo
         extends [mscorlib]System.Object
  {
    .field public int32 no
    .field public string bone
    .field public string name
    .field public int32 group
    .field public int32 level
    .field public int32 sync
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(int32 _no,
                                 string _bone,
                                 class [mscorlib]System.Collections.Generic.List`1<string> _lst) cil managed
    {
      // 代码大小       169 (0xa9)
      .maxstack  5
      .locals init (int32 V_0)
      IL_0000:  ldarg.0
      IL_0001:  ldstr      ""
      IL_0006:  stfld      string Studio.Info/BoneInfo::bone
      IL_000b:  ldarg.0
      IL_000c:  ldstr      ""
      IL_0011:  stfld      string Studio.Info/BoneInfo::name
      IL_0016:  ldarg.0
      IL_0017:  ldc.i4.m1
      IL_0018:  stfld      int32 Studio.Info/BoneInfo::group
      IL_001d:  ldarg.0
      IL_001e:  ldc.i4.m1
      IL_001f:  stfld      int32 Studio.Info/BoneInfo::sync
      IL_0024:  ldarg.0
      IL_0025:  call       instance void [mscorlib]System.Object::.ctor()
      IL_002a:  ldarg.0
      IL_002b:  ldarg.1
      IL_002c:  stfld      int32 Studio.Info/BoneInfo::no
      IL_0031:  ldarg.0
      IL_0032:  ldarg.2
      IL_0033:  stfld      string Studio.Info/BoneInfo::bone
      IL_0038:  ldc.i4.2
      IL_0039:  stloc.0
      IL_003a:  ldarg.0
      IL_003b:  ldarg.3
      IL_003c:  ldloc.0
      IL_003d:  dup
      IL_003e:  ldc.i4.1
      IL_003f:  add
      IL_0040:  stloc.0
      IL_0041:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0046:  stfld      string Studio.Info/BoneInfo::name
      IL_004b:  ldarg.3
      IL_004c:  ldloc.0
      IL_004d:  dup
      IL_004e:  ldc.i4.1
      IL_004f:  add
      IL_0050:  stloc.0
      IL_0051:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0056:  ldarg.0
      IL_0057:  ldflda     int32 Studio.Info/BoneInfo::group
      IL_005c:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0061:  brtrue.s   IL_006a

      IL_0063:  ldarg.0
      IL_0064:  ldc.i4.0
      IL_0065:  stfld      int32 Studio.Info/BoneInfo::group
      IL_006a:  ldarg.3
      IL_006b:  ldloc.0
      IL_006c:  dup
      IL_006d:  ldc.i4.1
      IL_006e:  add
      IL_006f:  stloc.0
      IL_0070:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0075:  ldarg.0
      IL_0076:  ldflda     int32 Studio.Info/BoneInfo::level
      IL_007b:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0080:  brtrue.s   IL_0089

      IL_0082:  ldarg.0
      IL_0083:  ldc.i4.0
      IL_0084:  stfld      int32 Studio.Info/BoneInfo::level
      IL_0089:  ldarg.3
      IL_008a:  ldloc.0
      IL_008b:  dup
      IL_008c:  ldc.i4.1
      IL_008d:  add
      IL_008e:  stloc.0
      IL_008f:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0094:  ldarg.0
      IL_0095:  ldflda     int32 Studio.Info/BoneInfo::sync
      IL_009a:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_009f:  brtrue.s   IL_00a8

      IL_00a1:  ldarg.0
      IL_00a2:  ldc.i4.m1
      IL_00a3:  stfld      int32 Studio.Info/BoneInfo::sync
      IL_00a8:  ret
    } // end of method BoneInfo::.ctor

  } // end of class BoneInfo

  .class auto ansi nested public beforefieldinit ItemLoadInfo
         extends Studio.Info/LoadCommonInfo
  {
    .field public class [mscorlib]System.Collections.Generic.List`1<string> bones
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(class [mscorlib]System.Collections.Generic.List`1<string> _lst) cil managed
    {
      // 代码大小       59 (0x3b)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void Studio.Info/LoadCommonInfo::.ctor()
      IL_0006:  ldarg.0
      IL_0007:  ldarg.1
      IL_0008:  ldc.i4.3
      IL_0009:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_000e:  stfld      string Studio.Info/LoadCommonInfo::name
      IL_0013:  ldarg.0
      IL_0014:  ldarg.1
      IL_0015:  ldc.i4.4
      IL_0016:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_001b:  stfld      string Studio.Info/FileInfo::manifest
      IL_0020:  ldarg.0
      IL_0021:  ldarg.1
      IL_0022:  ldc.i4.5
      IL_0023:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0028:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_002d:  ldarg.0
      IL_002e:  ldarg.1
      IL_002f:  ldc.i4.6
      IL_0030:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0035:  stfld      string Studio.Info/FileInfo::fileName
      IL_003a:  ret
    } // end of method ItemLoadInfo::.ctor

  } // end of class ItemLoadInfo

  .class auto ansi nested public beforefieldinit AccessoryGroupInfo
         extends [mscorlib]System.Object
  {
    .class auto ansi serializable sealed nested private beforefieldinit '<>c'
           extends [mscorlib]System.Object
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      .field public static initonly class Studio.Info/AccessoryGroupInfo/'<>c' '<>9'
      .field public static class [mscorlib]System.Func`2<string,int32> '<>9__8_0'
      .method private hidebysig specialname rtspecialname static 
              void  .cctor() cil managed
      {
        // 代码大小       11 (0xb)
        .maxstack  8
        IL_0000:  newobj     instance void Studio.Info/AccessoryGroupInfo/'<>c'::.ctor()
        IL_0005:  stsfld     class Studio.Info/AccessoryGroupInfo/'<>c' Studio.Info/AccessoryGroupInfo/'<>c'::'<>9'
        IL_000a:  ret
      } // end of method '<>c'::.cctor

      .method public hidebysig specialname rtspecialname 
              instance void  .ctor() cil managed
      {
        // 代码大小       7 (0x7)
        .maxstack  8
        IL_0000:  ldarg.0
        IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
        IL_0006:  ret
      } // end of method '<>c'::.ctor

      .method assembly hidebysig instance int32 
              '<.ctor>b__8_0'(string s) cil managed
      {
        // 代码大小       7 (0x7)
        .maxstack  8
        IL_0000:  ldarg.1
        IL_0001:  call       int32 [mscorlib]System.Int32::Parse(string)
        IL_0006:  ret
      } // end of method '<>c'::'<.ctor>b__8_0'

    } // end of class '<>c'

    .field private string '<Name>k__BackingField'
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field private int32[] '<Targets>k__BackingField'
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .method public hidebysig specialname 
            instance string  get_Name() cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      string Studio.Info/AccessoryGroupInfo::'<Name>k__BackingField'
      IL_0006:  ret
    } // end of method AccessoryGroupInfo::get_Name

    .method private hidebysig specialname 
            instance void  set_Name(string 'value') cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       8 (0x8)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldarg.1
      IL_0002:  stfld      string Studio.Info/AccessoryGroupInfo::'<Name>k__BackingField'
      IL_0007:  ret
    } // end of method AccessoryGroupInfo::set_Name

    .method public hidebysig specialname 
            instance int32[]  get_Targets() cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      int32[] Studio.Info/AccessoryGroupInfo::'<Targets>k__BackingField'
      IL_0006:  ret
    } // end of method AccessoryGroupInfo::get_Targets

    .method private hidebysig specialname 
            instance void  set_Targets(int32[] 'value') cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       8 (0x8)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldarg.1
      IL_0002:  stfld      int32[] Studio.Info/AccessoryGroupInfo::'<Targets>k__BackingField'
      IL_0007:  ret
    } // end of method AccessoryGroupInfo::set_Targets

    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(string _name,
                                 string _targets) cil managed
    {
      // 代码大小       89 (0x59)
      .maxstack  6
      IL_0000:  ldarg.0
      IL_0001:  ldstr      ""
      IL_0006:  stfld      string Studio.Info/AccessoryGroupInfo::'<Name>k__BackingField'
      IL_000b:  ldarg.0
      IL_000c:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0011:  ldarg.0
      IL_0012:  ldarg.1
      IL_0013:  call       instance void Studio.Info/AccessoryGroupInfo::set_Name(string)
      IL_0018:  ldarg.0
      IL_0019:  ldarg.2
      IL_001a:  ldc.i4.1
      IL_001b:  newarr     [mscorlib]System.Char
      IL_0020:  dup
      IL_0021:  ldc.i4.0
      IL_0022:  ldc.i4.s   45
      IL_0024:  stelem.i2
      IL_0025:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
      IL_002a:  ldsfld     class [mscorlib]System.Func`2<string,int32> Studio.Info/AccessoryGroupInfo/'<>c'::'<>9__8_0'
      IL_002f:  dup
      IL_0030:  brtrue.s   IL_0049

      IL_0032:  pop
      IL_0033:  ldsfld     class Studio.Info/AccessoryGroupInfo/'<>c' Studio.Info/AccessoryGroupInfo/'<>c'::'<>9'
      IL_0038:  ldftn      instance int32 Studio.Info/AccessoryGroupInfo/'<>c'::'<.ctor>b__8_0'(string)
      IL_003e:  newobj     instance void class [mscorlib]System.Func`2<string,int32>::.ctor(object,
                                                                                            native int)
      IL_0043:  dup
      IL_0044:  stsfld     class [mscorlib]System.Func`2<string,int32> Studio.Info/AccessoryGroupInfo/'<>c'::'<>9__8_0'
      IL_0049:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<string,int32>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                   class [mscorlib]System.Func`2<!!0,!!1>)
      IL_004e:  call       !!0[] [System.Core]System.Linq.Enumerable::ToArray<int32>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>)
      IL_0053:  call       instance void Studio.Info/AccessoryGroupInfo::set_Targets(int32[])
      IL_0058:  ret
    } // end of method AccessoryGroupInfo::.ctor

    .property instance string Name()
    {
      .get instance string Studio.Info/AccessoryGroupInfo::get_Name()
      .set instance void Studio.Info/AccessoryGroupInfo::set_Name(string)
    } // end of property AccessoryGroupInfo::Name
    .property instance int32[] Targets()
    {
      .get instance int32[] Studio.Info/AccessoryGroupInfo::get_Targets()
      .set instance void Studio.Info/AccessoryGroupInfo::set_Targets(int32[])
    } // end of property AccessoryGroupInfo::Targets
  } // end of class AccessoryGroupInfo

  .class auto ansi nested public beforefieldinit LightLoadInfo
         extends Studio.Info/LoadCommonInfo
  {
    .class auto ansi sealed nested public Target
           extends [mscorlib]System.Enum
    {
      .field public specialname rtspecialname int32 value__
      .field public static literal valuetype Studio.Info/LightLoadInfo/Target All = int32(0x00000000)
      .field public static literal valuetype Studio.Info/LightLoadInfo/Target Chara = int32(0x00000001)
      .field public static literal valuetype Studio.Info/LightLoadInfo/Target Map = int32(0x00000002)
    } // end of class Target

    .field public int32 no
    .field public valuetype Studio.Info/LightLoadInfo/Target target
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void Studio.Info/LoadCommonInfo::.ctor()
      IL_0006:  ret
    } // end of method LightLoadInfo::.ctor

  } // end of class LightLoadInfo

  .class auto ansi nested public beforefieldinit ParentageInfo
         extends [mscorlib]System.Object
  {
    .field public string parent
    .field public string child
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       29 (0x1d)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldstr      ""
      IL_0006:  stfld      string Studio.Info/ParentageInfo::parent
      IL_000b:  ldarg.0
      IL_000c:  ldstr      ""
      IL_0011:  stfld      string Studio.Info/ParentageInfo::child
      IL_0016:  ldarg.0
      IL_0017:  call       instance void [mscorlib]System.Object::.ctor()
      IL_001c:  ret
    } // end of method ParentageInfo::.ctor

  } // end of class ParentageInfo

  .class auto ansi nested public beforefieldinit OptionItemInfo
         extends Studio.Info/FileInfo
  {
    .field public class Studio.Info/FileInfo anmInfo
    .field public class Studio.Info/FileInfo anmOveride
    .field public class Studio.Info/ParentageInfo[] parentageInfo
    .field public bool counterScale
    .field public bool isAnimeSync
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       14 (0xe)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldc.i4.1
      IL_0002:  stfld      bool Studio.Info/OptionItemInfo::isAnimeSync
      IL_0007:  ldarg.0
      IL_0008:  call       instance void Studio.Info/FileInfo::.ctor()
      IL_000d:  ret
    } // end of method OptionItemInfo::.ctor

  } // end of class OptionItemInfo

  .class auto ansi nested public beforefieldinit AnimeLoadInfo
         extends Studio.Info/LoadCommonInfo
  {
    .class auto ansi sealed nested private beforefieldinit '<>c__DisplayClass3_0'
           extends [mscorlib]System.Object
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      .field public class Studio.Info/OptionItemInfo info
      .method public hidebysig specialname rtspecialname 
              instance void  .ctor() cil managed
      {
        // 代码大小       7 (0x7)
        .maxstack  8
        IL_0000:  ldarg.0
        IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
        IL_0006:  ret
      } // end of method '<>c__DisplayClass3_0'::.ctor

      .method assembly hidebysig instance void 
              '<LoadOption>b__0'(string _s) cil managed
      {
        // 代码大小       13 (0xd)
        .maxstack  8
        IL_0000:  ldarg.0
        IL_0001:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
        IL_0006:  ldarg.1
        IL_0007:  stfld      string Studio.Info/FileInfo::bundlePath
        IL_000c:  ret
      } // end of method '<>c__DisplayClass3_0'::'<LoadOption>b__0'

      .method assembly hidebysig instance void 
              '<LoadOption>b__1'(string _s) cil managed
      {
        // 代码大小       13 (0xd)
        .maxstack  8
        IL_0000:  ldarg.0
        IL_0001:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
        IL_0006:  ldarg.1
        IL_0007:  stfld      string Studio.Info/FileInfo::fileName
        IL_000c:  ret
      } // end of method '<>c__DisplayClass3_0'::'<LoadOption>b__1'

      .method assembly hidebysig instance void 
              '<LoadOption>b__2'(string _s) cil managed
      {
        // 代码大小       13 (0xd)
        .maxstack  8
        IL_0000:  ldarg.0
        IL_0001:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
        IL_0006:  ldarg.1
        IL_0007:  stfld      string Studio.Info/FileInfo::manifest
        IL_000c:  ret
      } // end of method '<>c__DisplayClass3_0'::'<LoadOption>b__2'

    } // end of class '<>c__DisplayClass3_0'

    .field public int32 sort
    .field public string clip
    .field public class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/OptionItemInfo> option
    .method public hidebysig static class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/OptionItemInfo> 
            LoadOption(class [mscorlib]System.Collections.Generic.List`1<string> _list,
                       int32 _start,
                       bool _animeSync) cil managed
    {
      // 代码大小       367 (0x16f)
      .maxstack  5
      .locals init (class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/OptionItemInfo> V_0,
               int32 V_1,
               class Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0' V_2)
      IL_0000:  newobj     instance void class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/OptionItemInfo>::.ctor()
      IL_0005:  stloc.0
      IL_0006:  ldarg.1
      IL_0007:  stloc.1
      IL_0008:  newobj     instance void Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::.ctor()
      IL_000d:  stloc.2
      IL_000e:  ldloc.2
      IL_000f:  newobj     instance void Studio.Info/OptionItemInfo::.ctor()
      IL_0014:  stfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
      IL_0019:  ldarg.0
      IL_001a:  ldloc.1
      IL_001b:  dup
      IL_001c:  ldc.i4.1
      IL_001d:  add
      IL_001e:  stloc.1
      IL_001f:  ldloc.2
      IL_0020:  ldftn      instance void Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::'<LoadOption>b__0'(string)
      IL_0026:  newobj     instance void class [mscorlib]System.Action`1<string>::.ctor(object,
                                                                                        native int)
      IL_002b:  call       bool [IL]NullCheck::SafeProc(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<string>,
                                                        int32,
                                                        class [mscorlib]System.Action`1<string>)
      IL_0030:  brfalse    IL_016d

      IL_0035:  ldarg.0
      IL_0036:  ldloc.1
      IL_0037:  dup
      IL_0038:  ldc.i4.1
      IL_0039:  add
      IL_003a:  stloc.1
      IL_003b:  ldloc.2
      IL_003c:  ldftn      instance void Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::'<LoadOption>b__1'(string)
      IL_0042:  newobj     instance void class [mscorlib]System.Action`1<string>::.ctor(object,
                                                                                        native int)
      IL_0047:  call       bool [IL]NullCheck::SafeProc(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<string>,
                                                        int32,
                                                        class [mscorlib]System.Action`1<string>)
      IL_004c:  brfalse    IL_016d

      IL_0051:  ldarg.0
      IL_0052:  ldloc.1
      IL_0053:  dup
      IL_0054:  ldc.i4.1
      IL_0055:  add
      IL_0056:  stloc.1
      IL_0057:  ldloc.2
      IL_0058:  ldftn      instance void Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::'<LoadOption>b__2'(string)
      IL_005e:  newobj     instance void class [mscorlib]System.Action`1<string>::.ctor(object,
                                                                                        native int)
      IL_0063:  call       bool [IL]NullCheck::SafeProc(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<string>,
                                                        int32,
                                                        class [mscorlib]System.Action`1<string>)
      IL_0068:  brfalse    IL_016d

      IL_006d:  ldloc.2
      IL_006e:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
      IL_0073:  newobj     instance void Studio.Info/FileInfo::.ctor()
      IL_0078:  stfld      class Studio.Info/FileInfo Studio.Info/OptionItemInfo::anmInfo
      IL_007d:  ldloc.2
      IL_007e:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
      IL_0083:  ldfld      class Studio.Info/FileInfo Studio.Info/OptionItemInfo::anmInfo
      IL_0088:  ldarg.0
      IL_0089:  ldloc.1
      IL_008a:  dup
      IL_008b:  ldc.i4.1
      IL_008c:  add
      IL_008d:  stloc.1
      IL_008e:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0093:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_0098:  ldloc.2
      IL_0099:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
      IL_009e:  ldfld      class Studio.Info/FileInfo Studio.Info/OptionItemInfo::anmInfo
      IL_00a3:  ldarg.0
      IL_00a4:  ldloc.1
      IL_00a5:  dup
      IL_00a6:  ldc.i4.1
      IL_00a7:  add
      IL_00a8:  stloc.1
      IL_00a9:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_00ae:  stfld      string Studio.Info/FileInfo::fileName
      IL_00b3:  ldloc.2
      IL_00b4:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
      IL_00b9:  newobj     instance void Studio.Info/FileInfo::.ctor()
      IL_00be:  stfld      class Studio.Info/FileInfo Studio.Info/OptionItemInfo::anmOveride
      IL_00c3:  ldloc.2
      IL_00c4:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
      IL_00c9:  ldfld      class Studio.Info/FileInfo Studio.Info/OptionItemInfo::anmOveride
      IL_00ce:  ldarg.0
      IL_00cf:  ldloc.1
      IL_00d0:  dup
      IL_00d1:  ldc.i4.1
      IL_00d2:  add
      IL_00d3:  stloc.1
      IL_00d4:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_00d9:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_00de:  ldloc.2
      IL_00df:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
      IL_00e4:  ldfld      class Studio.Info/FileInfo Studio.Info/OptionItemInfo::anmOveride
      IL_00e9:  ldarg.0
      IL_00ea:  ldloc.1
      IL_00eb:  dup
      IL_00ec:  ldc.i4.1
      IL_00ed:  add
      IL_00ee:  stloc.1
      IL_00ef:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_00f4:  stfld      string Studio.Info/FileInfo::fileName
      IL_00f9:  ldloc.2
      IL_00fa:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
      IL_00ff:  ldarg.0
      IL_0100:  ldloc.1
      IL_0101:  dup
      IL_0102:  ldc.i4.1
      IL_0103:  add
      IL_0104:  stloc.1
      IL_0105:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_010a:  call       class Studio.Info/ParentageInfo[] Studio.Info/AnimeLoadInfo::AnalysisParentageInfo(string)
      IL_010f:  stfld      class Studio.Info/ParentageInfo[] Studio.Info/OptionItemInfo::parentageInfo
      IL_0114:  ldarg.0
      IL_0115:  ldloc.1
      IL_0116:  dup
      IL_0117:  ldc.i4.1
      IL_0118:  add
      IL_0119:  stloc.1
      IL_011a:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_011f:  ldloc.2
      IL_0120:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
      IL_0125:  ldflda     bool Studio.Info/OptionItemInfo::counterScale
      IL_012a:  call       bool [mscorlib]System.Boolean::TryParse(string,
                                                                   bool&)
      IL_012f:  pop
      IL_0130:  ldarg.2
      IL_0131:  brfalse.s  IL_015c

      IL_0133:  ldarg.0
      IL_0134:  ldloc.1
      IL_0135:  dup
      IL_0136:  ldc.i4.1
      IL_0137:  add
      IL_0138:  stloc.1
      IL_0139:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_013e:  ldloc.2
      IL_013f:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
      IL_0144:  ldflda     bool Studio.Info/OptionItemInfo::isAnimeSync
      IL_0149:  call       bool [mscorlib]System.Boolean::TryParse(string,
                                                                   bool&)
      IL_014e:  brtrue.s   IL_015c

      IL_0150:  ldloc.2
      IL_0151:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
      IL_0156:  ldc.i4.1
      IL_0157:  stfld      bool Studio.Info/OptionItemInfo::isAnimeSync
      IL_015c:  ldloc.0
      IL_015d:  ldloc.2
      IL_015e:  ldfld      class Studio.Info/OptionItemInfo Studio.Info/AnimeLoadInfo/'<>c__DisplayClass3_0'::info
      IL_0163:  callvirt   instance void class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/OptionItemInfo>::Add(!0)
      IL_0168:  br         IL_0008

      IL_016d:  ldloc.0
      IL_016e:  ret
    } // end of method AnimeLoadInfo::LoadOption

    .method private hidebysig static class Studio.Info/ParentageInfo[] 
            AnalysisParentageInfo(string _str) cil managed
    {
      // 代码大小       116 (0x74)
      .maxstack  5
      .locals init (string[] V_0,
               class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/ParentageInfo> V_1,
               int32 V_2,
               string[] V_3,
               class Studio.Info/ParentageInfo V_4)
      IL_0000:  ldarg.0
      IL_0001:  call       bool [IL]NullCheck::IsNullOrEmpty(string)
      IL_0006:  brfalse.s  IL_000a

      IL_0008:  ldnull
      IL_0009:  ret

      IL_000a:  ldarg.0
      IL_000b:  ldc.i4.1
      IL_000c:  newarr     [mscorlib]System.Char
      IL_0011:  dup
      IL_0012:  ldc.i4.0
      IL_0013:  ldc.i4.s   44
      IL_0015:  stelem.i2
      IL_0016:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
      IL_001b:  stloc.0
      IL_001c:  newobj     instance void class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/ParentageInfo>::.ctor()
      IL_0021:  stloc.1
      IL_0022:  ldc.i4.0
      IL_0023:  stloc.2
      IL_0024:  br.s       IL_0067

      IL_0026:  ldloc.0
      IL_0027:  ldloc.2
      IL_0028:  ldelem.ref
      IL_0029:  ldc.i4.1
      IL_002a:  newarr     [mscorlib]System.Char
      IL_002f:  dup
      IL_0030:  ldc.i4.0
      IL_0031:  ldc.i4.s   47
      IL_0033:  stelem.i2
      IL_0034:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
      IL_0039:  stloc.3
      IL_003a:  newobj     instance void Studio.Info/ParentageInfo::.ctor()
      IL_003f:  stloc.s    V_4
      IL_0041:  ldloc.s    V_4
      IL_0043:  ldloc.3
      IL_0044:  ldc.i4.0
      IL_0045:  ldelem.ref
      IL_0046:  stfld      string Studio.Info/ParentageInfo::parent
      IL_004b:  ldloc.3
      IL_004c:  ldlen
      IL_004d:  conv.i4
      IL_004e:  ldc.i4.1
      IL_004f:  ble.s      IL_005b

      IL_0051:  ldloc.s    V_4
      IL_0053:  ldloc.3
      IL_0054:  ldc.i4.1
      IL_0055:  ldelem.ref
      IL_0056:  stfld      string Studio.Info/ParentageInfo::child
      IL_005b:  ldloc.1
      IL_005c:  ldloc.s    V_4
      IL_005e:  callvirt   instance void class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/ParentageInfo>::Add(!0)
      IL_0063:  ldloc.2
      IL_0064:  ldc.i4.1
      IL_0065:  add
      IL_0066:  stloc.2
      IL_0067:  ldloc.2
      IL_0068:  ldloc.0
      IL_0069:  ldlen
      IL_006a:  conv.i4
      IL_006b:  blt.s      IL_0026

      IL_006d:  ldloc.1
      IL_006e:  callvirt   instance !0[] class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/ParentageInfo>::ToArray()
      IL_0073:  ret
    } // end of method AnimeLoadInfo::AnalysisParentageInfo

    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       18 (0x12)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldstr      ""
      IL_0006:  stfld      string Studio.Info/AnimeLoadInfo::clip
      IL_000b:  ldarg.0
      IL_000c:  call       instance void Studio.Info/LoadCommonInfo::.ctor()
      IL_0011:  ret
    } // end of method AnimeLoadInfo::.ctor

  } // end of class AnimeLoadInfo

  .class auto ansi nested public beforefieldinit HAnimeLoadInfo
         extends Studio.Info/AnimeLoadInfo
  {
    .field public class Studio.Info/FileInfo overrideFile
    .field public int32 breastLayer
    .field public class Studio.Info/FileInfo yureFile
    .field public int32 motionID
    .field public int32 num
    .field public bool isMotion
    .field public bool[] pv
    .method public hidebysig specialname 
            instance bool  get_isBreastLayer() cil managed
    {
      // 代码大小       13 (0xd)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      int32 Studio.Info/HAnimeLoadInfo::breastLayer
      IL_0006:  ldc.i4.m1
      IL_0007:  ceq
      IL_0009:  ldc.i4.0
      IL_000a:  ceq
      IL_000c:  ret
    } // end of method HAnimeLoadInfo::get_isBreastLayer

    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(int32 _startIdx,
                                 class [mscorlib]System.Collections.Generic.List`1<string> _list) cil managed
    {
      // 代码大小       363 (0x16b)
      .maxstack  7
      .locals init (int32 V_0,
               int32 V_1,
               bool V_2)
      IL_0000:  ldarg.0
      IL_0001:  ldc.i4.m1
      IL_0002:  stfld      int32 Studio.Info/HAnimeLoadInfo::breastLayer
      IL_0007:  ldarg.0
      IL_0008:  call       instance void Studio.Info/AnimeLoadInfo::.ctor()
      IL_000d:  ldarg.1
      IL_000e:  stloc.0
      IL_000f:  ldarg.2
      IL_0010:  ldc.i4.0
      IL_0011:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0016:  ldarg.0
      IL_0017:  ldflda     int32 Studio.Info/AnimeLoadInfo::sort
      IL_001c:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0021:  pop
      IL_0022:  ldarg.0
      IL_0023:  ldarg.2
      IL_0024:  ldloc.0
      IL_0025:  dup
      IL_0026:  ldc.i4.1
      IL_0027:  add
      IL_0028:  stloc.0
      IL_0029:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_002e:  stfld      string Studio.Info/LoadCommonInfo::name
      IL_0033:  ldarg.0
      IL_0034:  ldarg.2
      IL_0035:  ldloc.0
      IL_0036:  dup
      IL_0037:  ldc.i4.1
      IL_0038:  add
      IL_0039:  stloc.0
      IL_003a:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_003f:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_0044:  ldarg.0
      IL_0045:  ldarg.2
      IL_0046:  ldloc.0
      IL_0047:  dup
      IL_0048:  ldc.i4.1
      IL_0049:  add
      IL_004a:  stloc.0
      IL_004b:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0050:  stfld      string Studio.Info/FileInfo::fileName
      IL_0055:  ldarg.0
      IL_0056:  newobj     instance void Studio.Info/FileInfo::.ctor()
      IL_005b:  dup
      IL_005c:  ldarg.2
      IL_005d:  ldloc.0
      IL_005e:  dup
      IL_005f:  ldc.i4.1
      IL_0060:  add
      IL_0061:  stloc.0
      IL_0062:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0067:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_006c:  dup
      IL_006d:  ldarg.2
      IL_006e:  ldloc.0
      IL_006f:  dup
      IL_0070:  ldc.i4.1
      IL_0071:  add
      IL_0072:  stloc.0
      IL_0073:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0078:  stfld      string Studio.Info/FileInfo::fileName
      IL_007d:  stfld      class Studio.Info/FileInfo Studio.Info/HAnimeLoadInfo::overrideFile
      IL_0082:  ldarg.0
      IL_0083:  ldarg.2
      IL_0084:  ldloc.0
      IL_0085:  dup
      IL_0086:  ldc.i4.1
      IL_0087:  add
      IL_0088:  stloc.0
      IL_0089:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_008e:  stfld      string Studio.Info/AnimeLoadInfo::clip
      IL_0093:  ldarg.2
      IL_0094:  ldloc.0
      IL_0095:  dup
      IL_0096:  ldc.i4.1
      IL_0097:  add
      IL_0098:  stloc.0
      IL_0099:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_009e:  ldarg.0
      IL_009f:  ldflda     int32 Studio.Info/HAnimeLoadInfo::breastLayer
      IL_00a4:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_00a9:  pop
      IL_00aa:  ldarg.0
      IL_00ab:  newobj     instance void Studio.Info/FileInfo::.ctor()
      IL_00b0:  dup
      IL_00b1:  ldarg.2
      IL_00b2:  ldloc.0
      IL_00b3:  dup
      IL_00b4:  ldc.i4.1
      IL_00b5:  add
      IL_00b6:  stloc.0
      IL_00b7:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_00bc:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_00c1:  dup
      IL_00c2:  ldarg.2
      IL_00c3:  ldloc.0
      IL_00c4:  dup
      IL_00c5:  ldc.i4.1
      IL_00c6:  add
      IL_00c7:  stloc.0
      IL_00c8:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_00cd:  stfld      string Studio.Info/FileInfo::fileName
      IL_00d2:  stfld      class Studio.Info/FileInfo Studio.Info/HAnimeLoadInfo::yureFile
      IL_00d7:  ldarg.2
      IL_00d8:  ldloc.0
      IL_00d9:  dup
      IL_00da:  ldc.i4.1
      IL_00db:  add
      IL_00dc:  stloc.0
      IL_00dd:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_00e2:  ldarg.0
      IL_00e3:  ldflda     int32 Studio.Info/HAnimeLoadInfo::motionID
      IL_00e8:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_00ed:  pop
      IL_00ee:  ldarg.2
      IL_00ef:  ldloc.0
      IL_00f0:  dup
      IL_00f1:  ldc.i4.1
      IL_00f2:  add
      IL_00f3:  stloc.0
      IL_00f4:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_00f9:  ldarg.0
      IL_00fa:  ldflda     int32 Studio.Info/HAnimeLoadInfo::num
      IL_00ff:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0104:  pop
      IL_0105:  ldarg.0
      IL_0106:  ldarg.2
      IL_0107:  ldloc.0
      IL_0108:  dup
      IL_0109:  ldc.i4.1
      IL_010a:  add
      IL_010b:  stloc.0
      IL_010c:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0111:  call       bool [mscorlib]System.Boolean::Parse(string)
      IL_0116:  stfld      bool Studio.Info/HAnimeLoadInfo::isMotion
      IL_011b:  ldarg.0
      IL_011c:  ldc.i4.1
      IL_011d:  ldc.i4.8
      IL_011e:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Repeat<bool>(!!0,
                                                                                                                                           int32)
      IL_0123:  call       !!0[] [System.Core]System.Linq.Enumerable::ToArray<bool>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>)
      IL_0128:  stfld      bool[] Studio.Info/HAnimeLoadInfo::pv
      IL_012d:  ldc.i4.0
      IL_012e:  stloc.1
      IL_012f:  br.s       IL_0154

      IL_0131:  ldc.i4.1
      IL_0132:  stloc.2
      IL_0133:  ldarg.2
      IL_0134:  ldloc.0
      IL_0135:  dup
      IL_0136:  ldc.i4.1
      IL_0137:  add
      IL_0138:  stloc.0
      IL_0139:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_013e:  ldloca.s   V_2
      IL_0140:  call       bool [mscorlib]System.Boolean::TryParse(string,
                                                                   bool&)
      IL_0145:  brfalse.s  IL_0150

      IL_0147:  ldarg.0
      IL_0148:  ldfld      bool[] Studio.Info/HAnimeLoadInfo::pv
      IL_014d:  ldloc.1
      IL_014e:  ldloc.2
      IL_014f:  stelem.i1
      IL_0150:  ldloc.1
      IL_0151:  ldc.i4.1
      IL_0152:  add
      IL_0153:  stloc.1
      IL_0154:  ldloc.1
      IL_0155:  ldc.i4.8
      IL_0156:  blt.s      IL_0131

      IL_0158:  ldarg.0
      IL_0159:  ldarg.2
      IL_015a:  ldloc.0
      IL_015b:  dup
      IL_015c:  ldc.i4.1
      IL_015d:  add
      IL_015e:  stloc.0
      IL_015f:  ldc.i4.0
      IL_0160:  call       class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/OptionItemInfo> Studio.Info/AnimeLoadInfo::LoadOption(class [mscorlib]System.Collections.Generic.List`1<string>,
                                                                                                                                                     int32,
                                                                                                                                                     bool)
      IL_0165:  stfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/OptionItemInfo> Studio.Info/AnimeLoadInfo::option
      IL_016a:  ret
    } // end of method HAnimeLoadInfo::.ctor

    .property instance bool isBreastLayer()
    {
      .get instance bool Studio.Info/HAnimeLoadInfo::get_isBreastLayer()
    } // end of property HAnimeLoadInfo::isBreastLayer
  } // end of class HAnimeLoadInfo

  .class auto ansi nested public beforefieldinit MapLoadInfo
         extends Studio.Info/LoadCommonInfo
  {
    .field public class Studio.Info/FileInfo vanish
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(class [mscorlib]System.Collections.Generic.List`1<string> _list) cil managed
    {
      // 代码大小       106 (0x6a)
      .maxstack  3
      IL_0000:  ldarg.0
      IL_0001:  call       instance void Studio.Info/LoadCommonInfo::.ctor()
      IL_0006:  ldarg.0
      IL_0007:  ldarg.1
      IL_0008:  ldc.i4.1
      IL_0009:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_000e:  stfld      string Studio.Info/LoadCommonInfo::name
      IL_0013:  ldarg.0
      IL_0014:  ldarg.1
      IL_0015:  ldc.i4.2
      IL_0016:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_001b:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_0020:  ldarg.0
      IL_0021:  ldarg.1
      IL_0022:  ldc.i4.3
      IL_0023:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0028:  stfld      string Studio.Info/FileInfo::fileName
      IL_002d:  ldarg.0
      IL_002e:  ldarg.1
      IL_002f:  ldc.i4.4
      IL_0030:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0035:  stfld      string Studio.Info/FileInfo::manifest
      IL_003a:  ldarg.0
      IL_003b:  newobj     instance void Studio.Info/FileInfo::.ctor()
      IL_0040:  stfld      class Studio.Info/FileInfo Studio.Info/MapLoadInfo::vanish
      IL_0045:  ldarg.0
      IL_0046:  ldfld      class Studio.Info/FileInfo Studio.Info/MapLoadInfo::vanish
      IL_004b:  ldarg.1
      IL_004c:  ldc.i4.5
      IL_004d:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0052:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_0057:  ldarg.0
      IL_0058:  ldfld      class Studio.Info/FileInfo Studio.Info/MapLoadInfo::vanish
      IL_005d:  ldarg.1
      IL_005e:  ldc.i4.6
      IL_005f:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0064:  stfld      string Studio.Info/FileInfo::fileName
      IL_0069:  ret
    } // end of method MapLoadInfo::.ctor

  } // end of class MapLoadInfo

  .class auto ansi nested public beforefieldinit SkyPatternInfo
         extends Studio.Info/LoadCommonInfo
  {
    .field private initonly valuetype [UnityEngine.CoreModule]UnityEngine.Vector3 '<Rotation>k__BackingField'
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .method public hidebysig specialname 
            instance valuetype [UnityEngine.CoreModule]UnityEngine.Vector3 
            get_Rotation() cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      valuetype [UnityEngine.CoreModule]UnityEngine.Vector3 Studio.Info/SkyPatternInfo::'<Rotation>k__BackingField'
      IL_0006:  ret
    } // end of method SkyPatternInfo::get_Rotation

    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(class [mscorlib]System.Collections.Generic.List`1<string> _list) cil managed
    {
      // 代码大小       162 (0xa2)
      .maxstack  5
      .locals init (int32 V_0,
               valuetype [UnityEngine.CoreModule]UnityEngine.Vector3 V_1)
      IL_0000:  ldarg.0
      IL_0001:  call       instance void Studio.Info/LoadCommonInfo::.ctor()
      IL_0006:  ldc.i4.1
      IL_0007:  stloc.0
      IL_0008:  ldarg.0
      IL_0009:  ldarg.1
      IL_000a:  ldloc.0
      IL_000b:  dup
      IL_000c:  ldc.i4.1
      IL_000d:  add
      IL_000e:  stloc.0
      IL_000f:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0014:  stfld      string Studio.Info/LoadCommonInfo::name
      IL_0019:  call       valuetype [UnityEngine.CoreModule]UnityEngine.Vector3 [UnityEngine.CoreModule]UnityEngine.Vector3::get_zero()
      IL_001e:  stloc.1
      IL_001f:  ldarg.1
      IL_0020:  ldloc.0
      IL_0021:  dup
      IL_0022:  ldc.i4.1
      IL_0023:  add
      IL_0024:  stloc.0
      IL_0025:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_002a:  ldloca.s   V_1
      IL_002c:  ldflda     float32 [UnityEngine.CoreModule]UnityEngine.Vector3::x
      IL_0031:  call       bool [mscorlib]System.Single::TryParse(string,
                                                                  float32&)
      IL_0036:  pop
      IL_0037:  ldarg.1
      IL_0038:  ldloc.0
      IL_0039:  dup
      IL_003a:  ldc.i4.1
      IL_003b:  add
      IL_003c:  stloc.0
      IL_003d:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0042:  ldloca.s   V_1
      IL_0044:  ldflda     float32 [UnityEngine.CoreModule]UnityEngine.Vector3::y
      IL_0049:  call       bool [mscorlib]System.Single::TryParse(string,
                                                                  float32&)
      IL_004e:  pop
      IL_004f:  ldarg.1
      IL_0050:  ldloc.0
      IL_0051:  dup
      IL_0052:  ldc.i4.1
      IL_0053:  add
      IL_0054:  stloc.0
      IL_0055:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_005a:  ldloca.s   V_1
      IL_005c:  ldflda     float32 [UnityEngine.CoreModule]UnityEngine.Vector3::z
      IL_0061:  call       bool [mscorlib]System.Single::TryParse(string,
                                                                  float32&)
      IL_0066:  pop
      IL_0067:  ldarg.0
      IL_0068:  ldloc.1
      IL_0069:  stfld      valuetype [UnityEngine.CoreModule]UnityEngine.Vector3 Studio.Info/SkyPatternInfo::'<Rotation>k__BackingField'
      IL_006e:  ldarg.0
      IL_006f:  ldarg.1
      IL_0070:  ldloc.0
      IL_0071:  dup
      IL_0072:  ldc.i4.1
      IL_0073:  add
      IL_0074:  stloc.0
      IL_0075:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_007a:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_007f:  ldarg.0
      IL_0080:  ldarg.1
      IL_0081:  ldloc.0
      IL_0082:  dup
      IL_0083:  ldc.i4.1
      IL_0084:  add
      IL_0085:  stloc.0
      IL_0086:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_008b:  stfld      string Studio.Info/FileInfo::fileName
      IL_0090:  ldarg.0
      IL_0091:  ldarg.1
      IL_0092:  ldloc.0
      IL_0093:  dup
      IL_0094:  ldc.i4.1
      IL_0095:  add
      IL_0096:  stloc.0
      IL_0097:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_009c:  stfld      string Studio.Info/FileInfo::manifest
      IL_00a1:  ret
    } // end of method SkyPatternInfo::.ctor

    .property instance valuetype [UnityEngine.CoreModule]UnityEngine.Vector3
            Rotation()
    {
      .get instance valuetype [UnityEngine.CoreModule]UnityEngine.Vector3 Studio.Info/SkyPatternInfo::get_Rotation()
    } // end of property SkyPatternInfo::Rotation
  } // end of class SkyPatternInfo

  .class auto ansi nested private beforefieldinit FileCheck
         extends [mscorlib]System.Object
  {
    .field private class [mscorlib]System.Collections.Generic.Dictionary`2<string,bool> dicConfirmed
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       18 (0x12)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ldarg.0
      IL_0007:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<string,bool>::.ctor()
      IL_000c:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<string,bool> Studio.Info/FileCheck::dicConfirmed
      IL_0011:  ret
    } // end of method FileCheck::.ctor

    .method public hidebysig instance bool 
            Check(string _path) cil managed
    {
      // 代码大小       73 (0x49)
      .maxstack  3
      .locals init (bool V_0)
      IL_0000:  ldarg.1
      IL_0001:  call       bool [IL]NullCheck::IsNullOrEmpty(string)
      IL_0006:  brfalse.s  IL_000a

      IL_0008:  ldc.i4.0
      IL_0009:  ret

      IL_000a:  ldc.i4.0
      IL_000b:  stloc.0
      IL_000c:  ldarg.0
      IL_000d:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<string,bool> Studio.Info/FileCheck::dicConfirmed
      IL_0012:  ldarg.1
      IL_0013:  ldloca.s   V_0
      IL_0015:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<string,bool>::TryGetValue(!0,
                                                                                                                           !1&)
      IL_001a:  brfalse.s  IL_001e

      IL_001c:  ldloc.0
      IL_001d:  ret

      IL_001e:  call       bool Studio.AssetBundleCheck::get_IsSimulation()
      IL_0023:  brfalse.s  IL_0029

      IL_0025:  ldc.i4.0
      IL_0026:  stloc.0
      IL_0027:  br.s       IL_003a

      IL_0029:  call       string AssetBundleManager::get_BaseDownloadingURL()
      IL_002e:  ldarg.1
      IL_002f:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_0034:  call       bool [mscorlib]System.IO.File::Exists(string)
      IL_0039:  stloc.0
      IL_003a:  ldarg.0
      IL_003b:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<string,bool> Studio.Info/FileCheck::dicConfirmed
      IL_0040:  ldarg.1
      IL_0041:  ldloc.0
      IL_0042:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<string,bool>::Add(!0,
                                                                                                                   !1)
      IL_0047:  ldloc.0
      IL_0048:  ret
    } // end of method FileCheck::Check

  } // end of class FileCheck

  .class auto ansi nested public beforefieldinit WaitTime
         extends [mscorlib]System.Object
  {
    .field private static literal float32 intervalTime = float32(2.9999999e-02)
    .field private float32 nextFrameTime
    .method public hidebysig specialname 
            instance bool  get_isOver() cil managed
    {
      // 代码大小       17 (0x11)
      .maxstack  8
      IL_0000:  call       float32 [UnityEngine.CoreModule]UnityEngine.Time::get_realtimeSinceStartup()
      IL_0005:  ldarg.0
      IL_0006:  ldfld      float32 Studio.Info/WaitTime::nextFrameTime
      IL_000b:  clt.un
      IL_000d:  ldc.i4.0
      IL_000e:  ceq
      IL_0010:  ret
    } // end of method WaitTime::get_isOver

    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       13 (0xd)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ldarg.0
      IL_0007:  call       instance void Studio.Info/WaitTime::Next()
      IL_000c:  ret
    } // end of method WaitTime::.ctor

    .method public hidebysig instance void 
            Next() cil managed
    {
      // 代码大小       18 (0x12)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       float32 [UnityEngine.CoreModule]UnityEngine.Time::get_realtimeSinceStartup()
      IL_0006:  ldc.r4     2.9999999e-02
      IL_000b:  add
      IL_000c:  stfld      float32 Studio.Info/WaitTime::nextFrameTime
      IL_0011:  ret
    } // end of method WaitTime::Next

    .property instance bool isOver()
    {
      .get instance bool Studio.Info/WaitTime::get_isOver()
    } // end of property WaitTime::isOver
  } // end of class WaitTime

  .class auto ansi nested private beforefieldinit FileListInfo
         extends [mscorlib]System.Object
  {
    .class auto ansi nested private beforefieldinit Data
           extends [mscorlib]System.Object
    {
      .class auto ansi serializable sealed nested private beforefieldinit '<>c'
             extends [mscorlib]System.Object
      {
        .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
        .field public static initonly class Studio.Info/FileListInfo/Data/'<>c' '<>9'
        .field public static class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool> '<>9__4_0'
        .method private hidebysig specialname rtspecialname static 
                void  .cctor() cil managed
        {
          // 代码大小       11 (0xb)
          .maxstack  8
          IL_0000:  newobj     instance void Studio.Info/FileListInfo/Data/'<>c'::.ctor()
          IL_0005:  stsfld     class Studio.Info/FileListInfo/Data/'<>c' Studio.Info/FileListInfo/Data/'<>c'::'<>9'
          IL_000a:  ret
        } // end of method '<>c'::.cctor

        .method public hidebysig specialname rtspecialname 
                instance void  .ctor() cil managed
        {
          // 代码大小       7 (0x7)
          .maxstack  8
          IL_0000:  ldarg.0
          IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
          IL_0006:  ret
        } // end of method '<>c'::.ctor

        .method assembly hidebysig instance bool 
                '<.ctor>b__4_0'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack> v) cil managed
        {
          // 代码大小       23 (0x17)
          .maxstack  8
          IL_0000:  ldarga.s   v
          IL_0002:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Key()
          IL_0007:  ldstr      "studio(\\d*)"
          IL_000c:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                      string)
          IL_0011:  callvirt   instance bool [System]System.Text.RegularExpressions.Group::get_Success()
          IL_0016:  ret
        } // end of method '<>c'::'<.ctor>b__4_0'

      } // end of class '<>c'

      .field private string[] files
      .field private initonly string manifest
      .method public hidebysig specialname 
              instance string  get_Manifest() cil managed
      {
        // 代码大小       7 (0x7)
        .maxstack  8
        IL_0000:  ldarg.0
        IL_0001:  ldfld      string Studio.Info/FileListInfo/Data::manifest
        IL_0006:  ret
      } // end of method Data::get_Manifest

      .method public hidebysig specialname rtspecialname 
              instance void  .ctor(string _path) cil managed
      {
        // 代码大小       147 (0x93)
        .maxstack  3
        .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>> V_0,
                 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack> V_1)
        IL_0000:  ldarg.0
        IL_0001:  ldstr      ""
        IL_0006:  stfld      string Studio.Info/FileListInfo/Data::manifest
        IL_000b:  ldarg.0
        IL_000c:  call       instance void [mscorlib]System.Object::.ctor()
        IL_0011:  ldarg.0
        IL_0012:  ldarg.1
        IL_0013:  ldc.i4.0
        IL_0014:  call       string[] Studio.AssetBundleCheck::GetAllFileName(string,
                                                                              bool)
        IL_0019:  stfld      string[] Studio.Info/FileListInfo/Data::files
        IL_001e:  call       class [mscorlib]System.Collections.Generic.Dictionary`2<string,class AssetBundleManager/BundlePack> AssetBundleManager::get_ManifestBundlePack()
        IL_0023:  ldsfld     class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool> Studio.Info/FileListInfo/Data/'<>c'::'<>9__4_0'
        IL_0028:  dup
        IL_0029:  brtrue.s   IL_0042

        IL_002b:  pop
        IL_002c:  ldsfld     class Studio.Info/FileListInfo/Data/'<>c' Studio.Info/FileListInfo/Data/'<>c'::'<>9'
        IL_0031:  ldftn      instance bool Studio.Info/FileListInfo/Data/'<>c'::'<.ctor>b__4_0'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>)
        IL_0037:  newobj     instance void class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool>::.ctor(object,
                                                                                                                                                                                                native int)
        IL_003c:  dup
        IL_003d:  stsfld     class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool> Studio.Info/FileListInfo/Data/'<>c'::'<>9__4_0'
        IL_0042:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Where<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                                                 class [mscorlib]System.Func`2<!!0,bool>)
        IL_0047:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>::GetEnumerator()
        IL_004c:  stloc.0
        .try
        {
          IL_004d:  br.s       IL_007e

          IL_004f:  ldloc.0
          IL_0050:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>::get_Current()
          IL_0055:  stloc.1
          IL_0056:  ldloca.s   V_1
          IL_0058:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Value()
          IL_005d:  callvirt   instance class [UnityEngine.AssetBundleModule]UnityEngine.AssetBundleManifest AssetBundleManager/BundlePack::get_AssetBundleManifest()
          IL_0062:  callvirt   instance string[] [UnityEngine.AssetBundleModule]UnityEngine.AssetBundleManifest::GetAllAssetBundles()
          IL_0067:  ldarg.1
          IL_0068:  call       bool [System.Core]System.Linq.Enumerable::Contains<string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                          !!0)
          IL_006d:  brfalse.s  IL_007e

          IL_006f:  ldarg.0
          IL_0070:  ldloca.s   V_1
          IL_0072:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Key()
          IL_0077:  stfld      string Studio.Info/FileListInfo/Data::manifest
          IL_007c:  leave.s    IL_0092

          IL_007e:  ldloc.0
          IL_007f:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
          IL_0084:  brtrue.s   IL_004f

          IL_0086:  leave.s    IL_0092

        }  // end .try
        finally
        {
          IL_0088:  ldloc.0
          IL_0089:  brfalse.s  IL_0091

          IL_008b:  ldloc.0
          IL_008c:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
          IL_0091:  endfinally
        }  // end handler
        IL_0092:  ret
      } // end of method Data::.ctor

      .method public hidebysig instance bool 
              Contains(string _file) cil managed
      {
        // 代码大小       13 (0xd)
        .maxstack  8
        IL_0000:  ldarg.0
        IL_0001:  ldfld      string[] Studio.Info/FileListInfo/Data::files
        IL_0006:  ldarg.1
        IL_0007:  call       bool [System.Core]System.Linq.Enumerable::Contains<string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                        !!0)
        IL_000c:  ret
      } // end of method Data::Contains

      .property instance string Manifest()
      {
        .get instance string Studio.Info/FileListInfo/Data::get_Manifest()
      } // end of property Data::Manifest
    } // end of class Data

    .field private class [mscorlib]System.Collections.Generic.Dictionary`2<string,class Studio.Info/FileListInfo/Data> dicFile
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(class [mscorlib]System.Collections.Generic.List`1<string> _list) cil managed
    {
      // 代码大小       78 (0x4e)
      .maxstack  3
      .locals init (valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<string> V_0,
               string V_1)
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ldarg.0
      IL_0007:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<string,class Studio.Info/FileListInfo/Data>::.ctor()
      IL_000c:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<string,class Studio.Info/FileListInfo/Data> Studio.Info/FileListInfo::dicFile
      IL_0011:  ldarg.1
      IL_0012:  callvirt   instance valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<!0> class [mscorlib]System.Collections.Generic.List`1<string>::GetEnumerator()
      IL_0017:  stloc.0
      .try
      {
        IL_0018:  br.s       IL_0034

        IL_001a:  ldloca.s   V_0
        IL_001c:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<string>::get_Current()
        IL_0021:  stloc.1
        IL_0022:  ldarg.0
        IL_0023:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<string,class Studio.Info/FileListInfo/Data> Studio.Info/FileListInfo::dicFile
        IL_0028:  ldloc.1
        IL_0029:  ldloc.1
        IL_002a:  newobj     instance void Studio.Info/FileListInfo/Data::.ctor(string)
        IL_002f:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<string,class Studio.Info/FileListInfo/Data>::Add(!0,
                                                                                                                                                    !1)
        IL_0034:  ldloca.s   V_0
        IL_0036:  call       instance bool valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<string>::MoveNext()
        IL_003b:  brtrue.s   IL_001a

        IL_003d:  leave.s    IL_004d

      }  // end .try
      finally
      {
        IL_003f:  ldloca.s   V_0
        IL_0041:  constrained. valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<string>
        IL_0047:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
        IL_004c:  endfinally
      }  // end handler
      IL_004d:  ret
    } // end of method FileListInfo::.ctor

    .method public hidebysig instance bool 
            Check(string _path,
                  string _file) cil managed
    {
      // 代码大小       43 (0x2b)
      .maxstack  3
      .locals init (class Studio.Info/FileListInfo/Data V_0)
      IL_0000:  ldnull
      IL_0001:  stloc.0
      IL_0002:  call       bool Studio.AssetBundleCheck::get_IsSimulation()
      IL_0007:  brtrue.s   IL_0011

      IL_0009:  ldarg.2
      IL_000a:  callvirt   instance string [mscorlib]System.String::ToLower()
      IL_000f:  starg.s    _file
      IL_0011:  ldarg.0
      IL_0012:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<string,class Studio.Info/FileListInfo/Data> Studio.Info/FileListInfo::dicFile
      IL_0017:  ldarg.1
      IL_0018:  ldloca.s   V_0
      IL_001a:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<string,class Studio.Info/FileListInfo/Data>::TryGetValue(!0,
                                                                                                                                                          !1&)
      IL_001f:  brtrue.s   IL_0023

      IL_0021:  ldc.i4.0
      IL_0022:  ret

      IL_0023:  ldloc.0
      IL_0024:  ldarg.2
      IL_0025:  callvirt   instance bool Studio.Info/FileListInfo/Data::Contains(string)
      IL_002a:  ret
    } // end of method FileListInfo::Check

    .method public hidebysig instance string 
            GetManifest(string _path) cil managed
    {
      // 代码大小       31 (0x1f)
      .maxstack  3
      .locals init (class Studio.Info/FileListInfo/Data V_0)
      IL_0000:  ldnull
      IL_0001:  stloc.0
      IL_0002:  ldarg.0
      IL_0003:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<string,class Studio.Info/FileListInfo/Data> Studio.Info/FileListInfo::dicFile
      IL_0008:  ldarg.1
      IL_0009:  ldloca.s   V_0
      IL_000b:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<string,class Studio.Info/FileListInfo/Data>::TryGetValue(!0,
                                                                                                                                                          !1&)
      IL_0010:  brtrue.s   IL_0018

      IL_0012:  ldstr      ""
      IL_0017:  ret

      IL_0018:  ldloc.0
      IL_0019:  callvirt   instance string Studio.Info/FileListInfo/Data::get_Manifest()
      IL_001e:  ret
    } // end of method FileListInfo::GetManifest

  } // end of class FileListInfo

  .class auto ansi sealed nested private LoadAnimeInfoCoroutineFunc
         extends [mscorlib]System.MulticastDelegate
  {
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(object 'object',
                                 native int 'method') runtime managed
    {
    } // end of method LoadAnimeInfoCoroutineFunc::.ctor

    .method public hidebysig newslot virtual 
            instance void  Invoke(class [IL]ExcelData _ed,
                                  class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> _dic) runtime managed
    {
    } // end of method LoadAnimeInfoCoroutineFunc::Invoke

    .method public hidebysig newslot virtual 
            instance class [mscorlib]System.IAsyncResult 
            BeginInvoke(class [IL]ExcelData _ed,
                        class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> _dic,
                        class [mscorlib]System.AsyncCallback callback,
                        object 'object') runtime managed
    {
    } // end of method LoadAnimeInfoCoroutineFunc::BeginInvoke

    .method public hidebysig newslot virtual 
            instance void  EndInvoke(class [mscorlib]System.IAsyncResult result) runtime managed
    {
    } // end of method LoadAnimeInfoCoroutineFunc::EndInvoke

  } // end of class LoadAnimeInfoCoroutineFunc

  .class auto ansi sealed nested private beforefieldinit '<LoadExcelDataCoroutine>d__58'
         extends [mscorlib]System.Object
         implements class [mscorlib]System.Collections.Generic.IEnumerator`1<object>,
                    [mscorlib]System.Collections.IEnumerator,
                    [mscorlib]System.IDisposable
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field private int32 '<>1__state'
    .field private object '<>2__current'
    .field public class Studio.Info '<>4__this'
    .field private class [mscorlib]System.Collections.Generic.List`1<string> '<pathList>5__2'
    .field private class Studio.Info/FileListInfo '<fli>5__3'
    .field private int32 '<i>5__4'
    .field private string '<bundlePath>5__5'
    .field private string '<fileName>5__6'
    .field private string '<manifest>5__7'
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(int32 '<>1__state') cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       14 (0xe)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ldarg.0
      IL_0007:  ldarg.1
      IL_0008:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_000d:  ret
    } // end of method '<LoadExcelDataCoroutine>d__58'::.ctor

    .method private hidebysig newslot virtual final 
            instance void  System.IDisposable.Dispose() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override [mscorlib]System.IDisposable::Dispose
      // 代码大小       1 (0x1)
      .maxstack  8
      IL_0000:  ret
    } // end of method '<LoadExcelDataCoroutine>d__58'::System.IDisposable.Dispose

    .method private hidebysig newslot virtual final 
            instance bool  MoveNext() cil managed
    {
      .override [mscorlib]System.Collections.IEnumerator::MoveNext
      // 代码大小       2509 (0x9cd)
      .maxstack  7
      .locals init (int32 V_0,
               class Studio.Info V_1,
               int32 V_2,
               int32 V_3)
      IL_0000:  ldarg.0
      IL_0001:  ldfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0006:  stloc.0
      IL_0007:  ldarg.0
      IL_0008:  ldfld      class Studio.Info Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>4__this'
      IL_000d:  stloc.1
      IL_000e:  ldloc.0
      IL_000f:  switch     ( 
                            IL_006e,
                            IL_012b,
                            IL_0176,
                            IL_02be,
                            IL_0338,
                            IL_0378,
                            IL_03aa,
                            IL_03df,
                            IL_044d,
                            IL_04c8,
                            IL_0543,
                            IL_0584,
                            IL_05c9,
                            IL_0603,
                            IL_0679,
                            IL_06c0,
                            IL_06f3,
                            IL_0763,
                            IL_07de,
                            IL_085f,
                            IL_08e0,
                            IL_095b)
      IL_006c:  ldc.i4.0
      IL_006d:  ret

      IL_006e:  ldarg.0
      IL_006f:  ldc.i4.m1
      IL_0070:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0075:  ldloc.1
      IL_0076:  call       instance bool Studio.Info::get_isLoadList()
      IL_007b:  brfalse.s  IL_007f

      IL_007d:  ldc.i4.0
      IL_007e:  ret

      IL_007f:  ldloc.1
      IL_0080:  newobj     instance void Studio.Info/FileCheck::.ctor()
      IL_0085:  stfld      class Studio.Info/FileCheck Studio.Info::fileCheck
      IL_008a:  ldloc.1
      IL_008b:  newobj     instance void Studio.Info/WaitTime::.ctor()
      IL_0090:  stfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0095:  ldloc.1
      IL_0096:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/BoneInfo> Studio.Info::dicBoneInfo
      IL_009b:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/BoneInfo>::Clear()
      IL_00a0:  ldloc.1
      IL_00a1:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicItemGroupCategory
      IL_00a6:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::Clear()
      IL_00ab:  ldloc.1
      IL_00ac:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>> Studio.Info::dicItemLoadInfo
      IL_00b1:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>>::Clear()
      IL_00b6:  ldloc.1
      IL_00b7:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LightLoadInfo> Studio.Info::dicLightLoadInfo
      IL_00bc:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LightLoadInfo>::Clear()
      IL_00c1:  ldloc.1
      IL_00c2:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicAGroupCategory
      IL_00c7:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::Clear()
      IL_00cc:  ldloc.1
      IL_00cd:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> Studio.Info::dicAnimeLoadInfo
      IL_00d2:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::Clear()
      IL_00d7:  ldloc.1
      IL_00d8:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicVoiceGroupCategory
      IL_00dd:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::Clear()
      IL_00e2:  ldloc.1
      IL_00e3:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>> Studio.Info::dicVoiceLoadInfo
      IL_00e8:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>>::Clear()
      IL_00ed:  ldloc.1
      IL_00ee:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> Studio.Info::dicColorGradingLoadInfo
      IL_00f3:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>::Clear()
      IL_00f8:  ldloc.1
      IL_00f9:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> Studio.Info::dicReflectionProbeLoadInfo
      IL_00fe:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>::Clear()
      IL_0103:  ldloc.1
      IL_0104:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/SkyPatternInfo> Studio.Info::dicSkyPatternInfo
      IL_0109:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/SkyPatternInfo>::Clear()
      IL_010e:  ldloc.1
      IL_010f:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0114:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_0119:  brfalse.s  IL_013d

      IL_011b:  ldarg.0
      IL_011c:  ldnull
      IL_011d:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_0122:  ldarg.0
      IL_0123:  ldc.i4.1
      IL_0124:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0129:  ldc.i4.1
      IL_012a:  ret

      IL_012b:  ldarg.0
      IL_012c:  ldc.i4.m1
      IL_012d:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0132:  ldloc.1
      IL_0133:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0138:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_013d:  ldarg.0
      IL_013e:  ldstr      "studio/info/"
      IL_0143:  ldc.i4.1
      IL_0144:  call       class [mscorlib]System.Collections.Generic.List`1<string> CommonLib::GetAssetBundleNameListFromPath(string,
                                                                                                                               bool)
      IL_0149:  stfld      class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<pathList>5__2'
      IL_014e:  ldarg.0
      IL_014f:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<pathList>5__2'
      IL_0154:  callvirt   instance void class [mscorlib]System.Collections.Generic.List`1<string>::Sort()
      IL_0159:  ldloc.1
      IL_015a:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_015f:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_0164:  brfalse.s  IL_0188

      IL_0166:  ldarg.0
      IL_0167:  ldnull
      IL_0168:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_016d:  ldarg.0
      IL_016e:  ldc.i4.2
      IL_016f:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0174:  ldc.i4.1
      IL_0175:  ret

      IL_0176:  ldarg.0
      IL_0177:  ldc.i4.m1
      IL_0178:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_017d:  ldloc.1
      IL_017e:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0183:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_0188:  ldarg.0
      IL_0189:  ldarg.0
      IL_018a:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<pathList>5__2'
      IL_018f:  newobj     instance void Studio.Info/FileListInfo::.ctor(class [mscorlib]System.Collections.Generic.List`1<string>)
      IL_0194:  stfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_0199:  ldarg.0
      IL_019a:  ldc.i4.0
      IL_019b:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<i>5__4'
      IL_01a0:  br         IL_09a0

      IL_01a5:  ldarg.0
      IL_01a6:  ldarg.0
      IL_01a7:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<pathList>5__2'
      IL_01ac:  ldarg.0
      IL_01ad:  ldfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<i>5__4'
      IL_01b2:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_01b7:  stfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_01bc:  ldarg.0
      IL_01bd:  ldarg.0
      IL_01be:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_01c3:  call       string [mscorlib]System.IO.Path::GetFileNameWithoutExtension(string)
      IL_01c8:  stfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_01cd:  ldarg.0
      IL_01ce:  ldarg.0
      IL_01cf:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_01d4:  ldarg.0
      IL_01d5:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_01da:  callvirt   instance string Studio.Info/FileListInfo::GetManifest(string)
      IL_01df:  stfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_01e4:  ldc.i4.0
      IL_01e5:  stloc.2
      IL_01e6:  ldarg.0
      IL_01e7:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_01ec:  ldloca.s   V_2
      IL_01ee:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_01f3:  brfalse.s  IL_0205

      IL_01f5:  ldloc.2
      IL_01f6:  ldc.i4.s   50
      IL_01f8:  blt.s      IL_0205

      IL_01fa:  ldloc.1
      IL_01fb:  call       instance bool Studio.Info::get_IsInstallAdd()
      IL_0200:  brfalse    IL_0990

      IL_0205:  ldarg.0
      IL_0206:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_020b:  ldarg.0
      IL_020c:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0211:  ldstr      "AccessoryPointGroup_"
      IL_0216:  ldarg.0
      IL_0217:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_021c:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_0221:  callvirt   instance bool Studio.Info/FileListInfo::Check(string,
                                                                         string)
      IL_0226:  brfalse.s  IL_0250

      IL_0228:  ldloc.1
      IL_0229:  ldloc.1
      IL_022a:  ldarg.0
      IL_022b:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0230:  ldstr      "AccessoryPointGroup_"
      IL_0235:  ldarg.0
      IL_0236:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_023b:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_0240:  ldarg.0
      IL_0241:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_0246:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                   string,
                                                                                   string)
      IL_024b:  call       instance void Studio.Info::LoadAccessoryGroupInfo(class [IL]ExcelData)
      IL_0250:  ldarg.0
      IL_0251:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_0256:  ldarg.0
      IL_0257:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_025c:  ldstr      "Bone_"
      IL_0261:  ldarg.0
      IL_0262:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0267:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_026c:  callvirt   instance bool Studio.Info/FileListInfo::Check(string,
                                                                         string)
      IL_0271:  brfalse.s  IL_02a1

      IL_0273:  ldloc.1
      IL_0274:  ldloc.1
      IL_0275:  ldarg.0
      IL_0276:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_027b:  ldstr      "Bone_"
      IL_0280:  ldarg.0
      IL_0281:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0286:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_028b:  ldarg.0
      IL_028c:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_0291:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                   string,
                                                                                   string)
      IL_0296:  ldloc.1
      IL_0297:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/BoneInfo> Studio.Info::dicBoneInfo
      IL_029c:  call       instance void Studio.Info::LoadBoneInfo(class [IL]ExcelData,
                                                                   class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/BoneInfo>)
      IL_02a1:  ldloc.1
      IL_02a2:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_02a7:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_02ac:  brfalse.s  IL_02d0

      IL_02ae:  ldarg.0
      IL_02af:  ldnull
      IL_02b0:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_02b5:  ldarg.0
      IL_02b6:  ldc.i4.3
      IL_02b7:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_02bc:  ldc.i4.1
      IL_02bd:  ret

      IL_02be:  ldarg.0
      IL_02bf:  ldc.i4.m1
      IL_02c0:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_02c5:  ldloc.1
      IL_02c6:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_02cb:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_02d0:  ldarg.0
      IL_02d1:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_02d6:  ldarg.0
      IL_02d7:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_02dc:  ldstr      "ItemGroup_"
      IL_02e1:  ldarg.0
      IL_02e2:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_02e7:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_02ec:  callvirt   instance bool Studio.Info/FileListInfo::Check(string,
                                                                         string)
      IL_02f1:  brfalse.s  IL_031b

      IL_02f3:  ldloc.1
      IL_02f4:  ldloc.1
      IL_02f5:  ldarg.0
      IL_02f6:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_02fb:  ldstr      "ItemGroup_"
      IL_0300:  ldarg.0
      IL_0301:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0306:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_030b:  ldarg.0
      IL_030c:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_0311:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                   string,
                                                                                   string)
      IL_0316:  call       instance void Studio.Info::LoadItemGroupInfo(class [IL]ExcelData)
      IL_031b:  ldloc.1
      IL_031c:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0321:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_0326:  brfalse.s  IL_034a

      IL_0328:  ldarg.0
      IL_0329:  ldnull
      IL_032a:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_032f:  ldarg.0
      IL_0330:  ldc.i4.4
      IL_0331:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0336:  ldc.i4.1
      IL_0337:  ret

      IL_0338:  ldarg.0
      IL_0339:  ldc.i4.m1
      IL_033a:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_033f:  ldloc.1
      IL_0340:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0345:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_034a:  ldloc.1
      IL_034b:  ldarg.0
      IL_034c:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0351:  ldstr      "ItemCategory_(\\d*)_(\\d*)"
      IL_0356:  call       instance void Studio.Info::LoadItemCategoryInfo(string,
                                                                           string)
      IL_035b:  ldloc.1
      IL_035c:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0361:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_0366:  brfalse.s  IL_038a

      IL_0368:  ldarg.0
      IL_0369:  ldnull
      IL_036a:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_036f:  ldarg.0
      IL_0370:  ldc.i4.5
      IL_0371:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0376:  ldc.i4.1
      IL_0377:  ret

      IL_0378:  ldarg.0
      IL_0379:  ldc.i4.m1
      IL_037a:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_037f:  ldloc.1
      IL_0380:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0385:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_038a:  ldarg.0
      IL_038b:  ldloc.1
      IL_038c:  ldarg.0
      IL_038d:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0392:  ldstr      "ItemList_(\\d*)_(\\d*)_(\\d*)"
      IL_0397:  call       instance class [mscorlib]System.Collections.IEnumerator Studio.Info::LoadItemLoadInfoCoroutine(string,
                                                                                                                          string)
      IL_039c:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_03a1:  ldarg.0
      IL_03a2:  ldc.i4.6
      IL_03a3:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_03a8:  ldc.i4.1
      IL_03a9:  ret

      IL_03aa:  ldarg.0
      IL_03ab:  ldc.i4.m1
      IL_03ac:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_03b1:  ldloc.1
      IL_03b2:  ldarg.0
      IL_03b3:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_03b8:  ldstr      "ItemBoneList_(\\d*)_(\\d*)"
      IL_03bd:  call       instance void Studio.Info::LoadItemBoneInfo(string,
                                                                       string)
      IL_03c2:  ldloc.1
      IL_03c3:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_03c8:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_03cd:  brfalse.s  IL_03f1

      IL_03cf:  ldarg.0
      IL_03d0:  ldnull
      IL_03d1:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_03d6:  ldarg.0
      IL_03d7:  ldc.i4.7
      IL_03d8:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_03dd:  ldc.i4.1
      IL_03de:  ret

      IL_03df:  ldarg.0
      IL_03e0:  ldc.i4.m1
      IL_03e1:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_03e6:  ldloc.1
      IL_03e7:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_03ec:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_03f1:  ldarg.0
      IL_03f2:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_03f7:  ldarg.0
      IL_03f8:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_03fd:  ldstr      "ItemData_"
      IL_0402:  ldarg.0
      IL_0403:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0408:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_040d:  callvirt   instance bool Studio.Info/FileListInfo::Check(string,
                                                                         string)
      IL_0412:  brfalse.s  IL_0430

      IL_0414:  ldloc.1
      IL_0415:  ldarg.0
      IL_0416:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_041b:  ldstr      "ItemData_"
      IL_0420:  ldarg.0
      IL_0421:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0426:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_042b:  call       instance void Studio.Info::LoadItemColorData(string,
                                                                        string)
      IL_0430:  ldloc.1
      IL_0431:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0436:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_043b:  brfalse.s  IL_045f

      IL_043d:  ldarg.0
      IL_043e:  ldnull
      IL_043f:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_0444:  ldarg.0
      IL_0445:  ldc.i4.8
      IL_0446:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_044b:  ldc.i4.1
      IL_044c:  ret

      IL_044d:  ldarg.0
      IL_044e:  ldc.i4.m1
      IL_044f:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0454:  ldloc.1
      IL_0455:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_045a:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_045f:  ldarg.0
      IL_0460:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_0465:  ldarg.0
      IL_0466:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_046b:  ldstr      "Light_"
      IL_0470:  ldarg.0
      IL_0471:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0476:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_047b:  callvirt   instance bool Studio.Info/FileListInfo::Check(string,
                                                                         string)
      IL_0480:  brfalse.s  IL_04aa

      IL_0482:  ldloc.1
      IL_0483:  ldloc.1
      IL_0484:  ldarg.0
      IL_0485:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_048a:  ldstr      "Light_"
      IL_048f:  ldarg.0
      IL_0490:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0495:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_049a:  ldarg.0
      IL_049b:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_04a0:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                   string,
                                                                                   string)
      IL_04a5:  call       instance void Studio.Info::LoadLightLoadInfo(class [IL]ExcelData)
      IL_04aa:  ldloc.1
      IL_04ab:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_04b0:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_04b5:  brfalse.s  IL_04da

      IL_04b7:  ldarg.0
      IL_04b8:  ldnull
      IL_04b9:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_04be:  ldarg.0
      IL_04bf:  ldc.i4.s   9
      IL_04c1:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_04c6:  ldc.i4.1
      IL_04c7:  ret

      IL_04c8:  ldarg.0
      IL_04c9:  ldc.i4.m1
      IL_04ca:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_04cf:  ldloc.1
      IL_04d0:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_04d5:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_04da:  ldarg.0
      IL_04db:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_04e0:  ldarg.0
      IL_04e1:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_04e6:  ldstr      "AnimeGroup_"
      IL_04eb:  ldarg.0
      IL_04ec:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_04f1:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_04f6:  callvirt   instance bool Studio.Info/FileListInfo::Check(string,
                                                                         string)
      IL_04fb:  brfalse.s  IL_0525

      IL_04fd:  ldloc.1
      IL_04fe:  ldloc.1
      IL_04ff:  ldarg.0
      IL_0500:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0505:  ldstr      "AnimeGroup_"
      IL_050a:  ldarg.0
      IL_050b:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0510:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_0515:  ldarg.0
      IL_0516:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_051b:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                   string,
                                                                                   string)
      IL_0520:  call       instance void Studio.Info::LoadAnimeGroupInfo(class [IL]ExcelData)
      IL_0525:  ldloc.1
      IL_0526:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_052b:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_0530:  brfalse.s  IL_0555

      IL_0532:  ldarg.0
      IL_0533:  ldnull
      IL_0534:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_0539:  ldarg.0
      IL_053a:  ldc.i4.s   10
      IL_053c:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0541:  ldc.i4.1
      IL_0542:  ret

      IL_0543:  ldarg.0
      IL_0544:  ldc.i4.m1
      IL_0545:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_054a:  ldloc.1
      IL_054b:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0550:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_0555:  ldloc.1
      IL_0556:  ldarg.0
      IL_0557:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_055c:  ldstr      "AnimeCategory_(\\d*)_(\\d*)"
      IL_0561:  call       instance void Studio.Info::LoadAnimeCategoryInfo(string,
                                                                            string)
      IL_0566:  ldloc.1
      IL_0567:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_056c:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_0571:  brfalse.s  IL_0596

      IL_0573:  ldarg.0
      IL_0574:  ldnull
      IL_0575:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_057a:  ldarg.0
      IL_057b:  ldc.i4.s   11
      IL_057d:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0582:  ldc.i4.1
      IL_0583:  ret

      IL_0584:  ldarg.0
      IL_0585:  ldc.i4.m1
      IL_0586:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_058b:  ldloc.1
      IL_058c:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0591:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_0596:  ldarg.0
      IL_0597:  ldloc.1
      IL_0598:  ldarg.0
      IL_0599:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_059e:  ldstr      "Anime_(\\d*)_(\\d*)_(\\d*)"
      IL_05a3:  ldloc.1
      IL_05a4:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> Studio.Info::dicAnimeLoadInfo
      IL_05a9:  ldloc.1
      IL_05aa:  ldftn      instance void Studio.Info::LoadAnimeLoadInfo(class [IL]ExcelData,
                                                                        class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>)
      IL_05b0:  newobj     instance void Studio.Info/LoadAnimeInfoCoroutineFunc::.ctor(object,
                                                                                       native int)
      IL_05b5:  call       instance class [mscorlib]System.Collections.IEnumerator Studio.Info::LoadAnimeLoadInfoCoroutine(string,
                                                                                                                           string,
                                                                                                                           class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>,
                                                                                                                           class Studio.Info/LoadAnimeInfoCoroutineFunc)
      IL_05ba:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_05bf:  ldarg.0
      IL_05c0:  ldc.i4.s   12
      IL_05c2:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_05c7:  ldc.i4.1
      IL_05c8:  ret

      IL_05c9:  ldarg.0
      IL_05ca:  ldc.i4.m1
      IL_05cb:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_05d0:  ldarg.0
      IL_05d1:  ldloc.1
      IL_05d2:  ldarg.0
      IL_05d3:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_05d8:  ldstr      "HAnime_(\\d*)_(\\d*)_(\\d*)"
      IL_05dd:  ldloc.1
      IL_05de:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> Studio.Info::dicAnimeLoadInfo
      IL_05e3:  ldloc.1
      IL_05e4:  ldftn      instance void Studio.Info::LoadHAnimeLoadInfo(class [IL]ExcelData,
                                                                         class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>)
      IL_05ea:  newobj     instance void Studio.Info/LoadAnimeInfoCoroutineFunc::.ctor(object,
                                                                                       native int)
      IL_05ef:  call       instance class [mscorlib]System.Collections.IEnumerator Studio.Info::LoadAnimeLoadInfoCoroutine(string,
                                                                                                                           string,
                                                                                                                           class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>,
                                                                                                                           class Studio.Info/LoadAnimeInfoCoroutineFunc)
      IL_05f4:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_05f9:  ldarg.0
      IL_05fa:  ldc.i4.s   13
      IL_05fc:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0601:  ldc.i4.1
      IL_0602:  ret

      IL_0603:  ldarg.0
      IL_0604:  ldc.i4.m1
      IL_0605:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_060a:  ldarg.0
      IL_060b:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_0610:  ldarg.0
      IL_0611:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0616:  ldstr      "VoiceGroup_"
      IL_061b:  ldarg.0
      IL_061c:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0621:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_0626:  callvirt   instance bool Studio.Info/FileListInfo::Check(string,
                                                                         string)
      IL_062b:  brfalse.s  IL_065b

      IL_062d:  ldloc.1
      IL_062e:  ldloc.1
      IL_062f:  ldarg.0
      IL_0630:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0635:  ldstr      "VoiceGroup_"
      IL_063a:  ldarg.0
      IL_063b:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0640:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_0645:  ldarg.0
      IL_0646:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_064b:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                   string,
                                                                                   string)
      IL_0650:  ldloc.1
      IL_0651:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicVoiceGroupCategory
      IL_0656:  call       instance void Studio.Info::LoadAnimeGroupInfo(class [IL]ExcelData,
                                                                         class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>)
      IL_065b:  ldloc.1
      IL_065c:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0661:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_0666:  brfalse.s  IL_068b

      IL_0668:  ldarg.0
      IL_0669:  ldnull
      IL_066a:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_066f:  ldarg.0
      IL_0670:  ldc.i4.s   14
      IL_0672:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0677:  ldc.i4.1
      IL_0678:  ret

      IL_0679:  ldarg.0
      IL_067a:  ldc.i4.m1
      IL_067b:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0680:  ldloc.1
      IL_0681:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0686:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_068b:  ldloc.1
      IL_068c:  ldarg.0
      IL_068d:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0692:  ldstr      "VoiceCategory_(\\d*)_(\\d*)"
      IL_0697:  ldloc.1
      IL_0698:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicVoiceGroupCategory
      IL_069d:  call       instance void Studio.Info::LoadAnimeCategoryInfo(string,
                                                                            string,
                                                                            class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>)
      IL_06a2:  ldloc.1
      IL_06a3:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_06a8:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_06ad:  brfalse.s  IL_06d2

      IL_06af:  ldarg.0
      IL_06b0:  ldnull
      IL_06b1:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_06b6:  ldarg.0
      IL_06b7:  ldc.i4.s   15
      IL_06b9:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_06be:  ldc.i4.1
      IL_06bf:  ret

      IL_06c0:  ldarg.0
      IL_06c1:  ldc.i4.m1
      IL_06c2:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_06c7:  ldloc.1
      IL_06c8:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_06cd:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_06d2:  ldarg.0
      IL_06d3:  ldloc.1
      IL_06d4:  ldarg.0
      IL_06d5:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_06da:  ldstr      "Voice_(\\d*)_(\\d*)_(\\d*)"
      IL_06df:  call       instance class [mscorlib]System.Collections.IEnumerator Studio.Info::LoadVoiceLoadInfoCoroutine(string,
                                                                                                                           string)
      IL_06e4:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_06e9:  ldarg.0
      IL_06ea:  ldc.i4.s   16
      IL_06ec:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_06f1:  ldc.i4.1
      IL_06f2:  ret

      IL_06f3:  ldarg.0
      IL_06f4:  ldc.i4.m1
      IL_06f5:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_06fa:  ldarg.0
      IL_06fb:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_0700:  ldarg.0
      IL_0701:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0706:  ldstr      "BGM_"
      IL_070b:  ldarg.0
      IL_070c:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0711:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_0716:  callvirt   instance bool Studio.Info/FileListInfo::Check(string,
                                                                         string)
      IL_071b:  brfalse.s  IL_0745

      IL_071d:  ldloc.1
      IL_071e:  ldloc.1
      IL_071f:  ldarg.0
      IL_0720:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0725:  ldstr      "BGM_"
      IL_072a:  ldarg.0
      IL_072b:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0730:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_0735:  ldarg.0
      IL_0736:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_073b:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                   string,
                                                                                   string)
      IL_0740:  call       instance void Studio.Info::LoadBGMLoadInfo(class [IL]ExcelData)
      IL_0745:  ldloc.1
      IL_0746:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_074b:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_0750:  brfalse.s  IL_0775

      IL_0752:  ldarg.0
      IL_0753:  ldnull
      IL_0754:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_0759:  ldarg.0
      IL_075a:  ldc.i4.s   17
      IL_075c:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0761:  ldc.i4.1
      IL_0762:  ret

      IL_0763:  ldarg.0
      IL_0764:  ldc.i4.m1
      IL_0765:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_076a:  ldloc.1
      IL_076b:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0770:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_0775:  ldarg.0
      IL_0776:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_077b:  ldarg.0
      IL_077c:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0781:  ldstr      "Map_"
      IL_0786:  ldarg.0
      IL_0787:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_078c:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_0791:  callvirt   instance bool Studio.Info/FileListInfo::Check(string,
                                                                         string)
      IL_0796:  brfalse.s  IL_07c0

      IL_0798:  ldloc.1
      IL_0799:  ldloc.1
      IL_079a:  ldarg.0
      IL_079b:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_07a0:  ldstr      "Map_"
      IL_07a5:  ldarg.0
      IL_07a6:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_07ab:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_07b0:  ldarg.0
      IL_07b1:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_07b6:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                   string,
                                                                                   string)
      IL_07bb:  call       instance void Studio.Info::LoadMapLoadInfo(class [IL]ExcelData)
      IL_07c0:  ldloc.1
      IL_07c1:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_07c6:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_07cb:  brfalse.s  IL_07f0

      IL_07cd:  ldarg.0
      IL_07ce:  ldnull
      IL_07cf:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_07d4:  ldarg.0
      IL_07d5:  ldc.i4.s   18
      IL_07d7:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_07dc:  ldc.i4.1
      IL_07dd:  ret

      IL_07de:  ldarg.0
      IL_07df:  ldc.i4.m1
      IL_07e0:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_07e5:  ldloc.1
      IL_07e6:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_07eb:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_07f0:  ldarg.0
      IL_07f1:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_07f6:  ldarg.0
      IL_07f7:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_07fc:  ldstr      "Filter_"
      IL_0801:  ldarg.0
      IL_0802:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0807:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_080c:  callvirt   instance bool Studio.Info/FileListInfo::Check(string,
                                                                         string)
      IL_0811:  brfalse.s  IL_0841

      IL_0813:  ldloc.1
      IL_0814:  ldloc.1
      IL_0815:  ldarg.0
      IL_0816:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_081b:  ldstr      "Filter_"
      IL_0820:  ldarg.0
      IL_0821:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0826:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_082b:  ldarg.0
      IL_082c:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_0831:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                   string,
                                                                                   string)
      IL_0836:  ldloc.1
      IL_0837:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> Studio.Info::dicColorGradingLoadInfo
      IL_083c:  call       instance void Studio.Info::LoadSoundLoadInfo(class [IL]ExcelData,
                                                                        class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>)
      IL_0841:  ldloc.1
      IL_0842:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0847:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_084c:  brfalse.s  IL_0871

      IL_084e:  ldarg.0
      IL_084f:  ldnull
      IL_0850:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_0855:  ldarg.0
      IL_0856:  ldc.i4.s   19
      IL_0858:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_085d:  ldc.i4.1
      IL_085e:  ret

      IL_085f:  ldarg.0
      IL_0860:  ldc.i4.m1
      IL_0861:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0866:  ldloc.1
      IL_0867:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_086c:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_0871:  ldarg.0
      IL_0872:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_0877:  ldarg.0
      IL_0878:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_087d:  ldstr      "Probe_"
      IL_0882:  ldarg.0
      IL_0883:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0888:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_088d:  callvirt   instance bool Studio.Info/FileListInfo::Check(string,
                                                                         string)
      IL_0892:  brfalse.s  IL_08c2

      IL_0894:  ldloc.1
      IL_0895:  ldloc.1
      IL_0896:  ldarg.0
      IL_0897:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_089c:  ldstr      "Probe_"
      IL_08a1:  ldarg.0
      IL_08a2:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_08a7:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_08ac:  ldarg.0
      IL_08ad:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_08b2:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                   string,
                                                                                   string)
      IL_08b7:  ldloc.1
      IL_08b8:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> Studio.Info::dicReflectionProbeLoadInfo
      IL_08bd:  call       instance void Studio.Info::LoadSoundLoadInfo(class [IL]ExcelData,
                                                                        class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>)
      IL_08c2:  ldloc.1
      IL_08c3:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_08c8:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_08cd:  brfalse.s  IL_08f2

      IL_08cf:  ldarg.0
      IL_08d0:  ldnull
      IL_08d1:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_08d6:  ldarg.0
      IL_08d7:  ldc.i4.s   20
      IL_08d9:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_08de:  ldc.i4.1
      IL_08df:  ret

      IL_08e0:  ldarg.0
      IL_08e1:  ldc.i4.m1
      IL_08e2:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_08e7:  ldloc.1
      IL_08e8:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_08ed:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_08f2:  ldarg.0
      IL_08f3:  ldfld      class Studio.Info/FileListInfo Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fli>5__3'
      IL_08f8:  ldarg.0
      IL_08f9:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_08fe:  ldstr      "StudioSky_"
      IL_0903:  ldarg.0
      IL_0904:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0909:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_090e:  callvirt   instance bool Studio.Info/FileListInfo::Check(string,
                                                                         string)
      IL_0913:  brfalse.s  IL_093d

      IL_0915:  ldloc.1
      IL_0916:  ldloc.1
      IL_0917:  ldarg.0
      IL_0918:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_091d:  ldstr      "StudioSky_"
      IL_0922:  ldarg.0
      IL_0923:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0928:  call       string [mscorlib]System.String::Concat(string,
                                                                  string)
      IL_092d:  ldarg.0
      IL_092e:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_0933:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                   string,
                                                                                   string)
      IL_0938:  call       instance void Studio.Info::LoadSkyPatternInfo(class [IL]ExcelData)
      IL_093d:  ldloc.1
      IL_093e:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0943:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
      IL_0948:  brfalse.s  IL_096d

      IL_094a:  ldarg.0
      IL_094b:  ldnull
      IL_094c:  stfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_0951:  ldarg.0
      IL_0952:  ldc.i4.s   21
      IL_0954:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0959:  ldc.i4.1
      IL_095a:  ret

      IL_095b:  ldarg.0
      IL_095c:  ldc.i4.m1
      IL_095d:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>1__state'
      IL_0962:  ldloc.1
      IL_0963:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_0968:  callvirt   instance void Studio.Info/WaitTime::Next()
      IL_096d:  ldarg.0
      IL_096e:  ldfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0973:  ldc.i4.1
      IL_0974:  ldnull
      IL_0975:  ldc.i4.0
      IL_0976:  call       void AssetBundleManager::UnloadAssetBundle(string,
                                                                      bool,
                                                                      string,
                                                                      bool)
      IL_097b:  ldarg.0
      IL_097c:  ldnull
      IL_097d:  stfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<bundlePath>5__5'
      IL_0982:  ldarg.0
      IL_0983:  ldnull
      IL_0984:  stfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<fileName>5__6'
      IL_0989:  ldarg.0
      IL_098a:  ldnull
      IL_098b:  stfld      string Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<manifest>5__7'
      IL_0990:  ldarg.0
      IL_0991:  ldfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<i>5__4'
      IL_0996:  ldc.i4.1
      IL_0997:  add
      IL_0998:  stloc.3
      IL_0999:  ldarg.0
      IL_099a:  ldloc.3
      IL_099b:  stfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<i>5__4'
      IL_09a0:  ldarg.0
      IL_09a1:  ldfld      int32 Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<i>5__4'
      IL_09a6:  ldarg.0
      IL_09a7:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<pathList>5__2'
      IL_09ac:  callvirt   instance int32 class [mscorlib]System.Collections.Generic.List`1<string>::get_Count()
      IL_09b1:  blt        IL_01a5

      IL_09b6:  ldloc.1
      IL_09b7:  ldnull
      IL_09b8:  stfld      class Studio.Info/FileCheck Studio.Info::fileCheck
      IL_09bd:  ldloc.1
      IL_09be:  ldnull
      IL_09bf:  stfld      class Studio.Info/WaitTime Studio.Info::waitTime
      IL_09c4:  ldloc.1
      IL_09c5:  ldc.i4.1
      IL_09c6:  call       instance void Studio.Info::set_isLoadList(bool)
      IL_09cb:  ldc.i4.0
      IL_09cc:  ret
    } // end of method '<LoadExcelDataCoroutine>d__58'::MoveNext

    .method private hidebysig newslot specialname virtual final 
            instance object  'System.Collections.Generic.IEnumerator<System.Object>.get_Current'() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override  method instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<object>::get_Current()
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_0006:  ret
    } // end of method '<LoadExcelDataCoroutine>d__58'::'System.Collections.Generic.IEnumerator<System.Object>.get_Current'

    .method private hidebysig newslot virtual final 
            instance void  System.Collections.IEnumerator.Reset() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override [mscorlib]System.Collections.IEnumerator::Reset
      // 代码大小       6 (0x6)
      .maxstack  8
      IL_0000:  newobj     instance void [mscorlib]System.NotSupportedException::.ctor()
      IL_0005:  throw
    } // end of method '<LoadExcelDataCoroutine>d__58'::System.Collections.IEnumerator.Reset

    .method private hidebysig newslot specialname virtual final 
            instance object  System.Collections.IEnumerator.get_Current() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override [mscorlib]System.Collections.IEnumerator::get_Current
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>2__current'
      IL_0006:  ret
    } // end of method '<LoadExcelDataCoroutine>d__58'::System.Collections.IEnumerator.get_Current

    .property instance object 'System.Collections.Generic.IEnumerator<System.Object>.Current'()
    {
      .get instance object Studio.Info/'<LoadExcelDataCoroutine>d__58'::'System.Collections.Generic.IEnumerator<System.Object>.get_Current'()
    } // end of property '<LoadExcelDataCoroutine>d__58'::'System.Collections.Generic.IEnumerator<System.Object>.Current'
    .property instance object System.Collections.IEnumerator.Current()
    {
      .get instance object Studio.Info/'<LoadExcelDataCoroutine>d__58'::System.Collections.IEnumerator.get_Current()
    } // end of property '<LoadExcelDataCoroutine>d__58'::System.Collections.IEnumerator.Current
  } // end of class '<LoadExcelDataCoroutine>d__58'

  .class auto ansi serializable sealed nested private beforefieldinit '<>c'
         extends [mscorlib]System.Object
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field public static initonly class Studio.Info/'<>c' '<>9'
    .field public static class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>,int32> '<>9__61_0'
    .field public static class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>,int32> '<>9__63_0'
    .field public static class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool> '<>9__67_0'
    .field public static class [mscorlib]System.Func`2<string,string> '<>9__67_1'
    .field public static class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool> '<>9__68_0'
    .field public static class [mscorlib]System.Func`2<string,string> '<>9__68_2'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__69_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__70_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__73_0'
    .field public static class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool> '<>9__75_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__76_0'
    .field public static class [mscorlib]System.Func`2<string,bool> '<>9__76_1'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__77_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__78_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__80_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__81_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__83_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__84_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__86_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__89_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__90_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__92_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__94_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__95_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__96_0'
    .field public static class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> '<>9__97_0'
    .method private hidebysig specialname rtspecialname static 
            void  .cctor() cil managed
    {
      // 代码大小       11 (0xb)
      .maxstack  8
      IL_0000:  newobj     instance void Studio.Info/'<>c'::.ctor()
      IL_0005:  stsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
      IL_000a:  ret
    } // end of method '<>c'::.cctor

    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ret
    } // end of method '<>c'::.ctor

    .method assembly hidebysig instance int32 
            '<ExistItemGroup>b__61_0'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>> _v) cil managed
    {
      // 代码大小       13 (0xd)
      .maxstack  8
      IL_0000:  ldarga.s   _v
      IL_0002:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>::get_Value()
      IL_0007:  callvirt   instance int32 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>::get_Count()
      IL_000c:  ret
    } // end of method '<>c'::'<ExistItemGroup>b__61_0'

    .method assembly hidebysig instance int32 
            '<ExistAnimeGroup>b__63_0'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>> _v) cil managed
    {
      // 代码大小       13 (0xd)
      .maxstack  8
      IL_0000:  ldarga.s   _v
      IL_0002:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>::get_Value()
      IL_0007:  callvirt   instance int32 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>::get_Count()
      IL_000c:  ret
    } // end of method '<>c'::'<ExistAnimeGroup>b__63_0'

    .method assembly hidebysig instance bool 
            '<FindAllAssetName>b__67_0'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack> v) cil managed
    {
      // 代码大小       23 (0x17)
      .maxstack  8
      IL_0000:  ldarga.s   v
      IL_0002:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Key()
      IL_0007:  ldstr      "studio(\\d*)"
      IL_000c:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                  string)
      IL_0011:  callvirt   instance bool [System]System.Text.RegularExpressions.Group::get_Success()
      IL_0016:  ret
    } // end of method '<>c'::'<FindAllAssetName>b__67_0'

    .method assembly hidebysig instance string 
            '<FindAllAssetName>b__67_1'(string s) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  call       string [mscorlib]System.IO.Path::GetFileNameWithoutExtension(string)
      IL_0006:  ret
    } // end of method '<>c'::'<FindAllAssetName>b__67_1'

    .method assembly hidebysig instance bool 
            '<FindAllAssetNameFromBundle>b__68_0'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack> v) cil managed
    {
      // 代码大小       23 (0x17)
      .maxstack  8
      IL_0000:  ldarga.s   v
      IL_0002:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Key()
      IL_0007:  ldstr      "studio(\\d*)"
      IL_000c:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                  string)
      IL_0011:  callvirt   instance bool [System]System.Text.RegularExpressions.Group::get_Success()
      IL_0016:  ret
    } // end of method '<>c'::'<FindAllAssetNameFromBundle>b__68_0'

    .method assembly hidebysig instance string 
            '<FindAllAssetNameFromBundle>b__68_2'(string s) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  call       string [mscorlib]System.IO.Path::GetFileNameWithoutExtension(string)
      IL_0006:  ret
    } // end of method '<>c'::'<FindAllAssetNameFromBundle>b__68_2'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadAccessoryGroupInfo>b__69_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadAccessoryGroupInfo>b__69_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadBoneInfo>b__70_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadBoneInfo>b__70_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadItemLoadInfo>b__73_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadItemLoadInfo>b__73_0'

    .method assembly hidebysig instance bool 
            '<LoadItemColorData>b__75_0'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack> v) cil managed
    {
      // 代码大小       23 (0x17)
      .maxstack  8
      IL_0000:  ldarga.s   v
      IL_0002:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Key()
      IL_0007:  ldstr      "studio(\\d*)"
      IL_000c:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                  string)
      IL_0011:  callvirt   instance bool [System]System.Text.RegularExpressions.Group::get_Success()
      IL_0016:  ret
    } // end of method '<>c'::'<LoadItemColorData>b__75_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadItemBoneInfo>b__76_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadItemBoneInfo>b__76_0'

    .method assembly hidebysig instance bool 
            '<LoadItemBoneInfo>b__76_1'(string s) cil managed
    {
      // 代码大小       10 (0xa)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  call       bool [IL]NullCheck::IsNullOrEmpty(string)
      IL_0006:  ldc.i4.0
      IL_0007:  ceq
      IL_0009:  ret
    } // end of method '<>c'::'<LoadItemBoneInfo>b__76_1'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadLightLoadInfo>b__77_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadLightLoadInfo>b__77_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadAnimeGroupInfo>b__78_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadAnimeGroupInfo>b__78_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadAnimeCategoryInfo>b__80_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadAnimeCategoryInfo>b__80_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadItemGroupInfo>b__81_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadItemGroupInfo>b__81_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadItemCategoryInfo>b__83_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadItemCategoryInfo>b__83_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadAnimeGroupInfo>b__84_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadAnimeGroupInfo>b__84_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadAnimeCategoryInfo>b__86_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadAnimeCategoryInfo>b__86_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadAnimeLoadInfo>b__89_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadAnimeLoadInfo>b__89_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadHAnimeLoadInfo>b__90_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadHAnimeLoadInfo>b__90_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadVoiceLoadInfo>b__92_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadVoiceLoadInfo>b__92_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadSoundLoadInfo>b__94_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadSoundLoadInfo>b__94_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadBGMLoadInfo>b__95_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadBGMLoadInfo>b__95_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadMapLoadInfo>b__96_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadMapLoadInfo>b__96_0'

    .method assembly hidebysig instance class [mscorlib]System.Collections.Generic.List`1<string> 
            '<LoadSkyPatternInfo>b__97_0'(class [IL]ExcelData/Param v) cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<string> [IL]ExcelData/Param::list
      IL_0006:  ret
    } // end of method '<>c'::'<LoadSkyPatternInfo>b__97_0'

  } // end of class '<>c'

  .class auto ansi sealed nested private beforefieldinit '<>c__DisplayClass67_0'
         extends [mscorlib]System.Object
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field public string _regex
    .field public class [mscorlib]System.Func`2<string,bool> '<>9__2'
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ret
    } // end of method '<>c__DisplayClass67_0'::.ctor

    .method assembly hidebysig instance bool 
            '<FindAllAssetName>b__2'(string s) cil managed
    {
      // 代码大小       19 (0x13)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldarg.0
      IL_0002:  ldfld      string Studio.Info/'<>c__DisplayClass67_0'::_regex
      IL_0007:  ldc.i4.1
      IL_0008:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                  string,
                                                                                                                                  valuetype [System]System.Text.RegularExpressions.RegexOptions)
      IL_000d:  callvirt   instance bool [System]System.Text.RegularExpressions.Group::get_Success()
      IL_0012:  ret
    } // end of method '<>c__DisplayClass67_0'::'<FindAllAssetName>b__2'

  } // end of class '<>c__DisplayClass67_0'

  .class auto ansi sealed nested private beforefieldinit '<>c__DisplayClass68_0'
         extends [mscorlib]System.Object
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field public string _bundlePath
    .field public string _regex
    .field public class [mscorlib]System.Func`2<string,bool> '<>9__3'
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ret
    } // end of method '<>c__DisplayClass68_0'::.ctor

    .method assembly hidebysig instance bool 
            '<FindAllAssetNameFromBundle>b__1'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack> v) cil managed
    {
      // 代码大小       29 (0x1d)
      .maxstack  8
      IL_0000:  ldarga.s   v
      IL_0002:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Value()
      IL_0007:  callvirt   instance class [UnityEngine.AssetBundleModule]UnityEngine.AssetBundleManifest AssetBundleManager/BundlePack::get_AssetBundleManifest()
      IL_000c:  callvirt   instance string[] [UnityEngine.AssetBundleModule]UnityEngine.AssetBundleManifest::GetAllAssetBundles()
      IL_0011:  ldarg.0
      IL_0012:  ldfld      string Studio.Info/'<>c__DisplayClass68_0'::_bundlePath
      IL_0017:  call       bool [System.Core]System.Linq.Enumerable::Contains<string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                      !!0)
      IL_001c:  ret
    } // end of method '<>c__DisplayClass68_0'::'<FindAllAssetNameFromBundle>b__1'

    .method assembly hidebysig instance bool 
            '<FindAllAssetNameFromBundle>b__3'(string s) cil managed
    {
      // 代码大小       19 (0x13)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldarg.0
      IL_0002:  ldfld      string Studio.Info/'<>c__DisplayClass68_0'::_regex
      IL_0007:  ldc.i4.1
      IL_0008:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                  string,
                                                                                                                                  valuetype [System]System.Text.RegularExpressions.RegexOptions)
      IL_000d:  callvirt   instance bool [System]System.Text.RegularExpressions.Group::get_Success()
      IL_0012:  ret
    } // end of method '<>c__DisplayClass68_0'::'<FindAllAssetNameFromBundle>b__3'

  } // end of class '<>c__DisplayClass68_0'

  .class auto ansi sealed nested private beforefieldinit '<LoadItemLoadInfoCoroutine>d__71'
         extends [mscorlib]System.Object
         implements class [mscorlib]System.Collections.Generic.IEnumerator`1<object>,
                    [mscorlib]System.Collections.IEnumerator,
                    [mscorlib]System.IDisposable
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field private int32 '<>1__state'
    .field private object '<>2__current'
    .field public class Studio.Info '<>4__this'
    .field public string _bundlePath
    .field public string _regex
    .field private string '<manifest>5__2'
    .field private valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> '<>7__wrap2'
    .field private valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> '<>7__wrap3'
    .field private valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> '<>7__wrap4'
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(int32 '<>1__state') cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       14 (0xe)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ldarg.0
      IL_0007:  ldarg.1
      IL_0008:  stfld      int32 Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>1__state'
      IL_000d:  ret
    } // end of method '<LoadItemLoadInfoCoroutine>d__71'::.ctor

    .method private hidebysig newslot virtual final 
            instance void  System.IDisposable.Dispose() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override [mscorlib]System.IDisposable::Dispose
      // 代码大小       69 (0x45)
      .maxstack  2
      .locals init (int32 V_0)
      IL_0000:  ldarg.0
      IL_0001:  ldfld      int32 Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>1__state'
      IL_0006:  stloc.0
      IL_0007:  ldloc.0
      IL_0008:  ldc.i4.s   -5
      IL_000a:  sub
      IL_000b:  ldc.i4.2
      IL_000c:  ble.un.s   IL_0012

      IL_000e:  ldloc.0
      IL_000f:  ldc.i4.1
      IL_0010:  bne.un.s   IL_0044

      IL_0012:  nop
      .try
      {
        IL_0013:  ldloc.0
        IL_0014:  ldc.i4.s   -5
        IL_0016:  sub
        IL_0017:  ldc.i4.1
        IL_0018:  ble.un.s   IL_0020

        IL_001a:  ldloc.0
        IL_001b:  ldc.i4.1
        IL_001c:  beq.s      IL_0020

        IL_001e:  leave.s    IL_0044

        IL_0020:  nop
        .try
        {
          IL_0021:  ldloc.0
          IL_0022:  ldc.i4.s   -5
          IL_0024:  beq.s      IL_002c

          IL_0026:  ldloc.0
          IL_0027:  ldc.i4.1
          IL_0028:  beq.s      IL_002c

          IL_002a:  leave.s    IL_0044

          IL_002c:  nop
          .try
          {
            IL_002d:  leave.s    IL_0044

          }  // end .try
          finally
          {
            IL_002f:  ldarg.0
            IL_0030:  call       instance void Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>m__Finally3'()
            IL_0035:  endfinally
          }  // end handler
        }  // end .try
        finally
        {
          IL_0036:  ldarg.0
          IL_0037:  call       instance void Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>m__Finally2'()
          IL_003c:  endfinally
        }  // end handler
      }  // end .try
      finally
      {
        IL_003d:  ldarg.0
        IL_003e:  call       instance void Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>m__Finally1'()
        IL_0043:  endfinally
      }  // end handler
      IL_0044:  ret
    } // end of method '<LoadItemLoadInfoCoroutine>d__71'::System.IDisposable.Dispose

    .method private hidebysig newslot virtual final 
            instance bool  MoveNext() cil managed
    {
      .override [mscorlib]System.Collections.IEnumerator::MoveNext
      // 代码大小       903 (0x387)
      .maxstack  5
      .locals init (bool V_0,
               int32 V_1,
               class Studio.Info V_2,
               string[] V_3,
               string V_4,
               class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> V_5,
               int32 V_6,
               string V_7,
               int32 V_8,
               int32 V_9,
               int32 V_10,
               valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> V_11,
               valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_12,
               valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string> V_13)
      .try
      {
        IL_0000:  ldarg.0
        IL_0001:  ldfld      int32 Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>1__state'
        IL_0006:  stloc.1
        IL_0007:  ldarg.0
        IL_0008:  ldfld      class Studio.Info Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>4__this'
        IL_000d:  stloc.2
        IL_000e:  ldloc.1
        IL_000f:  brfalse.s  IL_001f

        IL_0011:  ldloc.1
        IL_0012:  ldc.i4.1
        IL_0013:  beq        IL_0304

        IL_0018:  ldc.i4.0
        IL_0019:  stloc.0
        IL_001a:  leave      IL_0385

        IL_001f:  ldarg.0
        IL_0020:  ldc.i4.m1
        IL_0021:  stfld      int32 Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>1__state'
        IL_0026:  ldarg.0
        IL_0027:  ldstr      ""
        IL_002c:  stfld      string Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<manifest>5__2'
        IL_0031:  ldloc.2
        IL_0032:  ldarg.0
        IL_0033:  ldfld      string Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::_bundlePath
        IL_0038:  ldarg.0
        IL_0039:  ldfld      string Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::_regex
        IL_003e:  ldarg.0
        IL_003f:  ldflda     string Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<manifest>5__2'
        IL_0044:  call       instance string[] Studio.Info::FindAllAssetName(string,
                                                                             string,
                                                                             string&)
        IL_0049:  stloc.3
        IL_004a:  ldloc.3
        IL_004b:  call       bool [IL]NullCheck::IsNullOrEmpty<string>(class [mscorlib]System.Collections.Generic.IReadOnlyCollection`1<!!0>)
        IL_0050:  brfalse.s  IL_0059

        IL_0052:  ldc.i4.0
        IL_0053:  stloc.0
        IL_0054:  leave      IL_0385

        IL_0059:  ldarg.0
        IL_005a:  ldfld      string Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::_regex
        IL_005f:  ldc.i4.1
        IL_0060:  newarr     [mscorlib]System.Char
        IL_0065:  dup
        IL_0066:  ldc.i4.0
        IL_0067:  ldc.i4.s   95
        IL_0069:  stelem.i2
        IL_006a:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
        IL_006f:  ldc.i4.0
        IL_0070:  ldelem.ref
        IL_0071:  callvirt   instance string [mscorlib]System.String::ToLower()
        IL_0076:  stloc.s    V_4
        IL_0078:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::.ctor()
        IL_007d:  stloc.s    V_5
        IL_007f:  ldc.i4.0
        IL_0080:  stloc.s    V_6
        IL_0082:  br         IL_023d

        IL_0087:  ldloc.3
        IL_0088:  ldloc.s    V_6
        IL_008a:  ldelem.ref
        IL_008b:  call       string [mscorlib]System.IO.Path::GetFileNameWithoutExtension(string)
        IL_0090:  stloc.s    V_7
        IL_0092:  ldloc.s    V_7
        IL_0094:  ldc.i4.1
        IL_0095:  newarr     [mscorlib]System.Char
        IL_009a:  dup
        IL_009b:  ldc.i4.0
        IL_009c:  ldc.i4.s   95
        IL_009e:  stelem.i2
        IL_009f:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
        IL_00a4:  ldc.i4.0
        IL_00a5:  ldelem.ref
        IL_00a6:  callvirt   instance string [mscorlib]System.String::ToLower()
        IL_00ab:  ldloc.s    V_4
        IL_00ad:  callvirt   instance int32 [mscorlib]System.String::CompareTo(string)
        IL_00b2:  brtrue     IL_0237

        IL_00b7:  ldloc.s    V_7
        IL_00b9:  ldarg.0
        IL_00ba:  ldfld      string Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::_regex
        IL_00bf:  ldc.i4.1
        IL_00c0:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                    string,
                                                                                                                                    valuetype [System]System.Text.RegularExpressions.RegexOptions)
        IL_00c5:  dup
        IL_00c6:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
        IL_00cb:  ldc.i4.1
        IL_00cc:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
        IL_00d1:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
        IL_00d6:  call       int32 [mscorlib]System.Int32::Parse(string)
        IL_00db:  stloc.s    V_8
        IL_00dd:  dup
        IL_00de:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
        IL_00e3:  ldc.i4.2
        IL_00e4:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
        IL_00e9:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
        IL_00ee:  call       int32 [mscorlib]System.Int32::Parse(string)
        IL_00f3:  stloc.s    V_9
        IL_00f5:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
        IL_00fa:  ldc.i4.3
        IL_00fb:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
        IL_0100:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
        IL_0105:  call       int32 [mscorlib]System.Int32::Parse(string)
        IL_010a:  stloc.s    V_10
        IL_010c:  ldloc.s    V_9
        IL_010e:  ldc.i4.1
        IL_010f:  sub
        IL_0110:  switch     ( 
                              IL_0147,
                              IL_018e,
                              IL_01a1,
                              IL_01c6,
                              IL_01ce,
                              IL_01ce,
                              IL_01ce,
                              IL_01ce,
                              IL_01b6)
        IL_0139:  ldloc.s    V_9
        IL_013b:  ldc.i4.s   12
        IL_013d:  beq        IL_01c6

        IL_0142:  br         IL_01ce

        IL_0147:  ldloc.s    V_10
        IL_0149:  ldc.i4.1
        IL_014a:  sub
        IL_014b:  switch     ( 
                              IL_016e,
                              IL_016e,
                              IL_016e,
                              IL_016e,
                              IL_017b,
                              IL_017b,
                              IL_016e)
        IL_016c:  br.s       IL_01ce

        IL_016e:  ldloc.2
        IL_016f:  call       instance bool Studio.Info::get_IsInstallAI()
        IL_0174:  brtrue.s   IL_01ce

        IL_0176:  br         IL_0237

        IL_017b:  ldloc.s    V_8
        IL_017d:  ldc.i4.s   10
        IL_017f:  beq.s      IL_01ce

        IL_0181:  ldloc.2
        IL_0182:  call       instance bool Studio.Info::get_IsInstallAI()
        IL_0187:  brtrue.s   IL_01ce

        IL_0189:  br         IL_0237

        IL_018e:  ldloc.s    V_8
        IL_0190:  ldc.i4.s   13
        IL_0192:  beq.s      IL_01ce

        IL_0194:  ldloc.2
        IL_0195:  call       instance bool Studio.Info::get_IsInstallAI()
        IL_019a:  brtrue.s   IL_01ce

        IL_019c:  br         IL_0237

        IL_01a1:  ldloc.s    V_10
        IL_01a3:  ldc.i4.s   15
        IL_01a5:  sub
        IL_01a6:  ldc.i4.2
        IL_01a7:  bgt.un.s   IL_01ce

        IL_01a9:  ldloc.2
        IL_01aa:  call       instance bool Studio.Info::get_IsInstallAI()
        IL_01af:  brtrue.s   IL_01ce

        IL_01b1:  br         IL_0237

        IL_01b6:  ldloc.s    V_10
        IL_01b8:  ldc.i4.s   38
        IL_01ba:  bne.un.s   IL_01ce

        IL_01bc:  ldloc.2
        IL_01bd:  call       instance bool Studio.Info::get_IsInstallAI()
        IL_01c2:  brtrue.s   IL_01ce

        IL_01c4:  br.s       IL_0237

        IL_01c6:  ldloc.2
        IL_01c7:  call       instance bool Studio.Info::get_IsInstallAI()
        IL_01cc:  brfalse.s  IL_0237

        IL_01ce:  ldloc.s    V_8
        IL_01d0:  ldc.i4.s   50
        IL_01d2:  bne.un.s   IL_01dc

        IL_01d4:  ldloc.2
        IL_01d5:  call       instance bool Studio.Info::get_IsInstallAdd()
        IL_01da:  brfalse.s  IL_0237

        IL_01dc:  ldloc.s    V_5
        IL_01de:  ldloc.s    V_9
        IL_01e0:  callvirt   instance bool class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::ContainsKey(!0)
        IL_01e5:  brtrue.s   IL_01f5

        IL_01e7:  ldloc.s    V_5
        IL_01e9:  ldloc.s    V_9
        IL_01eb:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::.ctor()
        IL_01f0:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::Add(!0,
                                                                                                                                                                                                                                                                !1)
        IL_01f5:  ldloc.s    V_5
        IL_01f7:  ldloc.s    V_9
        IL_01f9:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Item(!0)
        IL_01fe:  ldloc.s    V_10
        IL_0200:  callvirt   instance bool class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::ContainsKey(!0)
        IL_0205:  brtrue.s   IL_021c

        IL_0207:  ldloc.s    V_5
        IL_0209:  ldloc.s    V_9
        IL_020b:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Item(!0)
        IL_0210:  ldloc.s    V_10
        IL_0212:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::.ctor()
        IL_0217:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::Add(!0,
                                                                                                                                                                                             !1)
        IL_021c:  ldloc.s    V_5
        IL_021e:  ldloc.s    V_9
        IL_0220:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Item(!0)
        IL_0225:  ldloc.s    V_10
        IL_0227:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Item(!0)
        IL_022c:  ldloc.s    V_8
        IL_022e:  ldloc.3
        IL_022f:  ldloc.s    V_6
        IL_0231:  ldelem.ref
        IL_0232:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::Add(!0,
                                                                                                                          !1)
        IL_0237:  ldloc.s    V_6
        IL_0239:  ldc.i4.1
        IL_023a:  add
        IL_023b:  stloc.s    V_6
        IL_023d:  ldloc.s    V_6
        IL_023f:  ldloc.3
        IL_0240:  ldlen
        IL_0241:  conv.i4
        IL_0242:  blt        IL_0087

        IL_0247:  ldarg.0
        IL_0248:  ldloc.s    V_5
        IL_024a:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::GetEnumerator()
        IL_024f:  stfld      valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap2'
        IL_0254:  ldarg.0
        IL_0255:  ldc.i4.s   -3
        IL_0257:  stfld      int32 Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>1__state'
        IL_025c:  br         IL_0358

        IL_0261:  ldarg.0
        IL_0262:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap2'
        IL_0267:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Current()
        IL_026c:  stloc.s    V_11
        IL_026e:  ldarg.0
        IL_026f:  ldloca.s   V_11
        IL_0271:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Value()
        IL_0276:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::GetEnumerator()
        IL_027b:  stfld      valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap3'
        IL_0280:  ldarg.0
        IL_0281:  ldc.i4.s   -4
        IL_0283:  stfld      int32 Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>1__state'
        IL_0288:  br         IL_0336

        IL_028d:  ldarg.0
        IL_028e:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap3'
        IL_0293:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Current()
        IL_0298:  stloc.s    V_12
        IL_029a:  ldarg.0
        IL_029b:  ldloca.s   V_12
        IL_029d:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Value()
        IL_02a2:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::GetEnumerator()
        IL_02a7:  stfld      valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap4'
        IL_02ac:  ldarg.0
        IL_02ad:  ldc.i4.s   -5
        IL_02af:  stfld      int32 Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>1__state'
        IL_02b4:  br.s       IL_0317

        IL_02b6:  ldarg.0
        IL_02b7:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap4'
        IL_02bc:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::get_Current()
        IL_02c1:  stloc.s    V_13
        IL_02c3:  ldloc.2
        IL_02c4:  ldloc.2
        IL_02c5:  ldarg.0
        IL_02c6:  ldfld      string Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::_bundlePath
        IL_02cb:  ldloca.s   V_13
        IL_02cd:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string>::get_Value()
        IL_02d2:  ldarg.0
        IL_02d3:  ldfld      string Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<manifest>5__2'
        IL_02d8:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                     string,
                                                                                     string)
        IL_02dd:  call       instance void Studio.Info::LoadItemLoadInfo(class [IL]ExcelData)
        IL_02e2:  ldloc.2
        IL_02e3:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
        IL_02e8:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
        IL_02ed:  brfalse.s  IL_0317

        IL_02ef:  ldarg.0
        IL_02f0:  ldnull
        IL_02f1:  stfld      object Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>2__current'
        IL_02f6:  ldarg.0
        IL_02f7:  ldc.i4.1
        IL_02f8:  stfld      int32 Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>1__state'
        IL_02fd:  ldc.i4.1
        IL_02fe:  stloc.0
        IL_02ff:  leave      IL_0385

        IL_0304:  ldarg.0
        IL_0305:  ldc.i4.s   -5
        IL_0307:  stfld      int32 Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>1__state'
        IL_030c:  ldloc.2
        IL_030d:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
        IL_0312:  callvirt   instance void Studio.Info/WaitTime::Next()
        IL_0317:  ldarg.0
        IL_0318:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap4'
        IL_031d:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::MoveNext()
        IL_0322:  brtrue.s   IL_02b6

        IL_0324:  ldarg.0
        IL_0325:  call       instance void Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>m__Finally3'()
        IL_032a:  ldarg.0
        IL_032b:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap4'
        IL_0330:  initobj    valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>
        IL_0336:  ldarg.0
        IL_0337:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap3'
        IL_033c:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::MoveNext()
        IL_0341:  brtrue     IL_028d

        IL_0346:  ldarg.0
        IL_0347:  call       instance void Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>m__Finally2'()
        IL_034c:  ldarg.0
        IL_034d:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap3'
        IL_0352:  initobj    valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>
        IL_0358:  ldarg.0
        IL_0359:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap2'
        IL_035e:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::MoveNext()
        IL_0363:  brtrue     IL_0261

        IL_0368:  ldarg.0
        IL_0369:  call       instance void Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>m__Finally1'()
        IL_036e:  ldarg.0
        IL_036f:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap2'
        IL_0374:  initobj    valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>
        IL_037a:  ldc.i4.0
        IL_037b:  stloc.0
        IL_037c:  leave.s    IL_0385

      }  // end .try
      fault
      {
        IL_037e:  ldarg.0
        IL_037f:  call       instance void Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::System.IDisposable.Dispose()
        IL_0384:  endfinally
      }  // end handler
      IL_0385:  ldloc.0
      IL_0386:  ret
    } // end of method '<LoadItemLoadInfoCoroutine>d__71'::MoveNext

    .method private hidebysig instance void 
            '<>m__Finally1'() cil managed
    {
      // 代码大小       25 (0x19)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldc.i4.m1
      IL_0002:  stfld      int32 Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>1__state'
      IL_0007:  ldarg.0
      IL_0008:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap2'
      IL_000d:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>
      IL_0013:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0018:  ret
    } // end of method '<LoadItemLoadInfoCoroutine>d__71'::'<>m__Finally1'

    .method private hidebysig instance void 
            '<>m__Finally2'() cil managed
    {
      // 代码大小       26 (0x1a)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldc.i4.s   -3
      IL_0003:  stfld      int32 Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>1__state'
      IL_0008:  ldarg.0
      IL_0009:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap3'
      IL_000e:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>
      IL_0014:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0019:  ret
    } // end of method '<LoadItemLoadInfoCoroutine>d__71'::'<>m__Finally2'

    .method private hidebysig instance void 
            '<>m__Finally3'() cil managed
    {
      // 代码大小       26 (0x1a)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldc.i4.s   -4
      IL_0003:  stfld      int32 Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>1__state'
      IL_0008:  ldarg.0
      IL_0009:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>7__wrap4'
      IL_000e:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>
      IL_0014:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0019:  ret
    } // end of method '<LoadItemLoadInfoCoroutine>d__71'::'<>m__Finally3'

    .method private hidebysig newslot specialname virtual final 
            instance object  'System.Collections.Generic.IEnumerator<System.Object>.get_Current'() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override  method instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<object>::get_Current()
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      object Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>2__current'
      IL_0006:  ret
    } // end of method '<LoadItemLoadInfoCoroutine>d__71'::'System.Collections.Generic.IEnumerator<System.Object>.get_Current'

    .method private hidebysig newslot virtual final 
            instance void  System.Collections.IEnumerator.Reset() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override [mscorlib]System.Collections.IEnumerator::Reset
      // 代码大小       6 (0x6)
      .maxstack  8
      IL_0000:  newobj     instance void [mscorlib]System.NotSupportedException::.ctor()
      IL_0005:  throw
    } // end of method '<LoadItemLoadInfoCoroutine>d__71'::System.Collections.IEnumerator.Reset

    .method private hidebysig newslot specialname virtual final 
            instance object  System.Collections.IEnumerator.get_Current() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override [mscorlib]System.Collections.IEnumerator::get_Current
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      object Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>2__current'
      IL_0006:  ret
    } // end of method '<LoadItemLoadInfoCoroutine>d__71'::System.Collections.IEnumerator.get_Current

    .property instance object 'System.Collections.Generic.IEnumerator<System.Object>.Current'()
    {
      .get instance object Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'System.Collections.Generic.IEnumerator<System.Object>.get_Current'()
    } // end of property '<LoadItemLoadInfoCoroutine>d__71'::'System.Collections.Generic.IEnumerator<System.Object>.Current'
    .property instance object System.Collections.IEnumerator.Current()
    {
      .get instance object Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::System.Collections.IEnumerator.get_Current()
    } // end of property '<LoadItemLoadInfoCoroutine>d__71'::System.Collections.IEnumerator.Current
  } // end of class '<LoadItemLoadInfoCoroutine>d__71'

  .class auto ansi sealed nested private beforefieldinit '<>c__DisplayClass75_0'
         extends [mscorlib]System.Object
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field public string _bundlePath
    .field public class [mscorlib]System.Predicate`1<string> '<>9__1'
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ret
    } // end of method '<>c__DisplayClass75_0'::.ctor

    .method assembly hidebysig instance bool 
            '<LoadItemColorData>b__1'(string s) cil managed
    {
      // 代码大小       13 (0xd)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldarg.0
      IL_0002:  ldfld      string Studio.Info/'<>c__DisplayClass75_0'::_bundlePath
      IL_0007:  call       bool [mscorlib]System.String::op_Equality(string,
                                                                     string)
      IL_000c:  ret
    } // end of method '<>c__DisplayClass75_0'::'<LoadItemColorData>b__1'

  } // end of class '<>c__DisplayClass75_0'

  .class auto ansi sealed nested private beforefieldinit '<LoadAnimeLoadInfoCoroutine>d__88'
         extends [mscorlib]System.Object
         implements class [mscorlib]System.Collections.Generic.IEnumerator`1<object>,
                    [mscorlib]System.Collections.IEnumerator,
                    [mscorlib]System.IDisposable
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field private int32 '<>1__state'
    .field private object '<>2__current'
    .field public class Studio.Info '<>4__this'
    .field public string _bundlePath
    .field public string _regex
    .field public class Studio.Info/LoadAnimeInfoCoroutineFunc _func
    .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> _dic
    .field private string '<manifest>5__2'
    .field private valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> '<>7__wrap2'
    .field private valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> '<>7__wrap3'
    .field private valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> '<>7__wrap4'
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(int32 '<>1__state') cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       14 (0xe)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ldarg.0
      IL_0007:  ldarg.1
      IL_0008:  stfld      int32 Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>1__state'
      IL_000d:  ret
    } // end of method '<LoadAnimeLoadInfoCoroutine>d__88'::.ctor

    .method private hidebysig newslot virtual final 
            instance void  System.IDisposable.Dispose() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override [mscorlib]System.IDisposable::Dispose
      // 代码大小       69 (0x45)
      .maxstack  2
      .locals init (int32 V_0)
      IL_0000:  ldarg.0
      IL_0001:  ldfld      int32 Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>1__state'
      IL_0006:  stloc.0
      IL_0007:  ldloc.0
      IL_0008:  ldc.i4.s   -5
      IL_000a:  sub
      IL_000b:  ldc.i4.2
      IL_000c:  ble.un.s   IL_0012

      IL_000e:  ldloc.0
      IL_000f:  ldc.i4.1
      IL_0010:  bne.un.s   IL_0044

      IL_0012:  nop
      .try
      {
        IL_0013:  ldloc.0
        IL_0014:  ldc.i4.s   -5
        IL_0016:  sub
        IL_0017:  ldc.i4.1
        IL_0018:  ble.un.s   IL_0020

        IL_001a:  ldloc.0
        IL_001b:  ldc.i4.1
        IL_001c:  beq.s      IL_0020

        IL_001e:  leave.s    IL_0044

        IL_0020:  nop
        .try
        {
          IL_0021:  ldloc.0
          IL_0022:  ldc.i4.s   -5
          IL_0024:  beq.s      IL_002c

          IL_0026:  ldloc.0
          IL_0027:  ldc.i4.1
          IL_0028:  beq.s      IL_002c

          IL_002a:  leave.s    IL_0044

          IL_002c:  nop
          .try
          {
            IL_002d:  leave.s    IL_0044

          }  // end .try
          finally
          {
            IL_002f:  ldarg.0
            IL_0030:  call       instance void Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>m__Finally3'()
            IL_0035:  endfinally
          }  // end handler
        }  // end .try
        finally
        {
          IL_0036:  ldarg.0
          IL_0037:  call       instance void Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>m__Finally2'()
          IL_003c:  endfinally
        }  // end handler
      }  // end .try
      finally
      {
        IL_003d:  ldarg.0
        IL_003e:  call       instance void Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>m__Finally1'()
        IL_0043:  endfinally
      }  // end handler
      IL_0044:  ret
    } // end of method '<LoadAnimeLoadInfoCoroutine>d__88'::System.IDisposable.Dispose

    .method private hidebysig newslot virtual final 
            instance bool  MoveNext() cil managed
    {
      .override [mscorlib]System.Collections.IEnumerator::MoveNext
      // 代码大小       713 (0x2c9)
      .maxstack  5
      .locals init (bool V_0,
               int32 V_1,
               class Studio.Info V_2,
               string[] V_3,
               string V_4,
               class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> V_5,
               int32 V_6,
               int32 V_7,
               int32 V_8,
               int32 V_9,
               valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> V_10,
               valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_11,
               valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string> V_12)
      .try
      {
        IL_0000:  ldarg.0
        IL_0001:  ldfld      int32 Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>1__state'
        IL_0006:  stloc.1
        IL_0007:  ldarg.0
        IL_0008:  ldfld      class Studio.Info Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>4__this'
        IL_000d:  stloc.2
        IL_000e:  ldloc.1
        IL_000f:  brfalse.s  IL_001f

        IL_0011:  ldloc.1
        IL_0012:  ldc.i4.1
        IL_0013:  beq        IL_0246

        IL_0018:  ldc.i4.0
        IL_0019:  stloc.0
        IL_001a:  leave      IL_02c7

        IL_001f:  ldarg.0
        IL_0020:  ldc.i4.m1
        IL_0021:  stfld      int32 Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>1__state'
        IL_0026:  ldarg.0
        IL_0027:  ldstr      ""
        IL_002c:  stfld      string Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<manifest>5__2'
        IL_0031:  ldloc.2
        IL_0032:  ldarg.0
        IL_0033:  ldfld      string Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::_bundlePath
        IL_0038:  ldarg.0
        IL_0039:  ldfld      string Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::_regex
        IL_003e:  ldarg.0
        IL_003f:  ldflda     string Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<manifest>5__2'
        IL_0044:  call       instance string[] Studio.Info::FindAllAssetName(string,
                                                                             string,
                                                                             string&)
        IL_0049:  stloc.3
        IL_004a:  ldloc.3
        IL_004b:  call       bool [IL]NullCheck::IsNullOrEmpty<string>(class [mscorlib]System.Collections.Generic.IReadOnlyCollection`1<!!0>)
        IL_0050:  brfalse.s  IL_0059

        IL_0052:  ldc.i4.0
        IL_0053:  stloc.0
        IL_0054:  leave      IL_02c7

        IL_0059:  ldarg.0
        IL_005a:  ldfld      string Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::_regex
        IL_005f:  ldc.i4.1
        IL_0060:  newarr     [mscorlib]System.Char
        IL_0065:  dup
        IL_0066:  ldc.i4.0
        IL_0067:  ldc.i4.s   95
        IL_0069:  stelem.i2
        IL_006a:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
        IL_006f:  ldc.i4.0
        IL_0070:  ldelem.ref
        IL_0071:  callvirt   instance string [mscorlib]System.String::ToLower()
        IL_0076:  stloc.s    V_4
        IL_0078:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::.ctor()
        IL_007d:  stloc.s    V_5
        IL_007f:  ldc.i4.0
        IL_0080:  stloc.s    V_6
        IL_0082:  br         IL_0174

        IL_0087:  ldloc.3
        IL_0088:  ldloc.s    V_6
        IL_008a:  ldelem.ref
        IL_008b:  ldc.i4.1
        IL_008c:  newarr     [mscorlib]System.Char
        IL_0091:  dup
        IL_0092:  ldc.i4.0
        IL_0093:  ldc.i4.s   95
        IL_0095:  stelem.i2
        IL_0096:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
        IL_009b:  ldc.i4.0
        IL_009c:  ldelem.ref
        IL_009d:  callvirt   instance string [mscorlib]System.String::ToLower()
        IL_00a2:  ldloc.s    V_4
        IL_00a4:  callvirt   instance int32 [mscorlib]System.String::CompareTo(string)
        IL_00a9:  brtrue     IL_016e

        IL_00ae:  ldloc.3
        IL_00af:  ldloc.s    V_6
        IL_00b1:  ldelem.ref
        IL_00b2:  ldarg.0
        IL_00b3:  ldfld      string Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::_regex
        IL_00b8:  ldc.i4.1
        IL_00b9:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                    string,
                                                                                                                                    valuetype [System]System.Text.RegularExpressions.RegexOptions)
        IL_00be:  dup
        IL_00bf:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
        IL_00c4:  ldc.i4.1
        IL_00c5:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
        IL_00ca:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
        IL_00cf:  call       int32 [mscorlib]System.Int32::Parse(string)
        IL_00d4:  stloc.s    V_7
        IL_00d6:  dup
        IL_00d7:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
        IL_00dc:  ldc.i4.2
        IL_00dd:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
        IL_00e2:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
        IL_00e7:  call       int32 [mscorlib]System.Int32::Parse(string)
        IL_00ec:  stloc.s    V_8
        IL_00ee:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
        IL_00f3:  ldc.i4.3
        IL_00f4:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
        IL_00f9:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
        IL_00fe:  call       int32 [mscorlib]System.Int32::Parse(string)
        IL_0103:  stloc.s    V_9
        IL_0105:  ldloc.s    V_7
        IL_0107:  ldc.i4.s   50
        IL_0109:  bne.un.s   IL_0113

        IL_010b:  ldloc.2
        IL_010c:  call       instance bool Studio.Info::get_IsInstallAdd()
        IL_0111:  brfalse.s  IL_016e

        IL_0113:  ldloc.s    V_5
        IL_0115:  ldloc.s    V_8
        IL_0117:  callvirt   instance bool class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::ContainsKey(!0)
        IL_011c:  brtrue.s   IL_012c

        IL_011e:  ldloc.s    V_5
        IL_0120:  ldloc.s    V_8
        IL_0122:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::.ctor()
        IL_0127:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::Add(!0,
                                                                                                                                                                                                                                                                !1)
        IL_012c:  ldloc.s    V_5
        IL_012e:  ldloc.s    V_8
        IL_0130:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Item(!0)
        IL_0135:  ldloc.s    V_9
        IL_0137:  callvirt   instance bool class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::ContainsKey(!0)
        IL_013c:  brtrue.s   IL_0153

        IL_013e:  ldloc.s    V_5
        IL_0140:  ldloc.s    V_8
        IL_0142:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Item(!0)
        IL_0147:  ldloc.s    V_9
        IL_0149:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::.ctor()
        IL_014e:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::Add(!0,
                                                                                                                                                                                             !1)
        IL_0153:  ldloc.s    V_5
        IL_0155:  ldloc.s    V_8
        IL_0157:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Item(!0)
        IL_015c:  ldloc.s    V_9
        IL_015e:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Item(!0)
        IL_0163:  ldloc.s    V_7
        IL_0165:  ldloc.3
        IL_0166:  ldloc.s    V_6
        IL_0168:  ldelem.ref
        IL_0169:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::Add(!0,
                                                                                                                          !1)
        IL_016e:  ldloc.s    V_6
        IL_0170:  ldc.i4.1
        IL_0171:  add
        IL_0172:  stloc.s    V_6
        IL_0174:  ldloc.s    V_6
        IL_0176:  ldloc.3
        IL_0177:  ldlen
        IL_0178:  conv.i4
        IL_0179:  blt        IL_0087

        IL_017e:  ldarg.0
        IL_017f:  ldloc.s    V_5
        IL_0181:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::GetEnumerator()
        IL_0186:  stfld      valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap2'
        IL_018b:  ldarg.0
        IL_018c:  ldc.i4.s   -3
        IL_018e:  stfld      int32 Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>1__state'
        IL_0193:  br         IL_029a

        IL_0198:  ldarg.0
        IL_0199:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap2'
        IL_019e:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Current()
        IL_01a3:  stloc.s    V_10
        IL_01a5:  ldarg.0
        IL_01a6:  ldloca.s   V_10
        IL_01a8:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Value()
        IL_01ad:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::GetEnumerator()
        IL_01b2:  stfld      valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap3'
        IL_01b7:  ldarg.0
        IL_01b8:  ldc.i4.s   -4
        IL_01ba:  stfld      int32 Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>1__state'
        IL_01bf:  br         IL_0278

        IL_01c4:  ldarg.0
        IL_01c5:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap3'
        IL_01ca:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Current()
        IL_01cf:  stloc.s    V_11
        IL_01d1:  ldarg.0
        IL_01d2:  ldloca.s   V_11
        IL_01d4:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Value()
        IL_01d9:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::GetEnumerator()
        IL_01de:  stfld      valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap4'
        IL_01e3:  ldarg.0
        IL_01e4:  ldc.i4.s   -5
        IL_01e6:  stfld      int32 Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>1__state'
        IL_01eb:  br.s       IL_0259

        IL_01ed:  ldarg.0
        IL_01ee:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap4'
        IL_01f3:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::get_Current()
        IL_01f8:  stloc.s    V_12
        IL_01fa:  ldarg.0
        IL_01fb:  ldfld      class Studio.Info/LoadAnimeInfoCoroutineFunc Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::_func
        IL_0200:  ldloc.2
        IL_0201:  ldarg.0
        IL_0202:  ldfld      string Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::_bundlePath
        IL_0207:  ldloca.s   V_12
        IL_0209:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string>::get_Value()
        IL_020e:  ldarg.0
        IL_020f:  ldfld      string Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<manifest>5__2'
        IL_0214:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                     string,
                                                                                     string)
        IL_0219:  ldarg.0
        IL_021a:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::_dic
        IL_021f:  callvirt   instance void Studio.Info/LoadAnimeInfoCoroutineFunc::Invoke(class [IL]ExcelData,
                                                                                          class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>)
        IL_0224:  ldloc.2
        IL_0225:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
        IL_022a:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
        IL_022f:  brfalse.s  IL_0259

        IL_0231:  ldarg.0
        IL_0232:  ldnull
        IL_0233:  stfld      object Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>2__current'
        IL_0238:  ldarg.0
        IL_0239:  ldc.i4.1
        IL_023a:  stfld      int32 Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>1__state'
        IL_023f:  ldc.i4.1
        IL_0240:  stloc.0
        IL_0241:  leave      IL_02c7

        IL_0246:  ldarg.0
        IL_0247:  ldc.i4.s   -5
        IL_0249:  stfld      int32 Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>1__state'
        IL_024e:  ldloc.2
        IL_024f:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
        IL_0254:  callvirt   instance void Studio.Info/WaitTime::Next()
        IL_0259:  ldarg.0
        IL_025a:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap4'
        IL_025f:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::MoveNext()
        IL_0264:  brtrue.s   IL_01ed

        IL_0266:  ldarg.0
        IL_0267:  call       instance void Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>m__Finally3'()
        IL_026c:  ldarg.0
        IL_026d:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap4'
        IL_0272:  initobj    valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>
        IL_0278:  ldarg.0
        IL_0279:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap3'
        IL_027e:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::MoveNext()
        IL_0283:  brtrue     IL_01c4

        IL_0288:  ldarg.0
        IL_0289:  call       instance void Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>m__Finally2'()
        IL_028e:  ldarg.0
        IL_028f:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap3'
        IL_0294:  initobj    valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>
        IL_029a:  ldarg.0
        IL_029b:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap2'
        IL_02a0:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::MoveNext()
        IL_02a5:  brtrue     IL_0198

        IL_02aa:  ldarg.0
        IL_02ab:  call       instance void Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>m__Finally1'()
        IL_02b0:  ldarg.0
        IL_02b1:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap2'
        IL_02b6:  initobj    valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>
        IL_02bc:  ldc.i4.0
        IL_02bd:  stloc.0
        IL_02be:  leave.s    IL_02c7

      }  // end .try
      fault
      {
        IL_02c0:  ldarg.0
        IL_02c1:  call       instance void Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::System.IDisposable.Dispose()
        IL_02c6:  endfinally
      }  // end handler
      IL_02c7:  ldloc.0
      IL_02c8:  ret
    } // end of method '<LoadAnimeLoadInfoCoroutine>d__88'::MoveNext

    .method private hidebysig instance void 
            '<>m__Finally1'() cil managed
    {
      // 代码大小       25 (0x19)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldc.i4.m1
      IL_0002:  stfld      int32 Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>1__state'
      IL_0007:  ldarg.0
      IL_0008:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap2'
      IL_000d:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>
      IL_0013:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0018:  ret
    } // end of method '<LoadAnimeLoadInfoCoroutine>d__88'::'<>m__Finally1'

    .method private hidebysig instance void 
            '<>m__Finally2'() cil managed
    {
      // 代码大小       26 (0x1a)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldc.i4.s   -3
      IL_0003:  stfld      int32 Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>1__state'
      IL_0008:  ldarg.0
      IL_0009:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap3'
      IL_000e:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>
      IL_0014:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0019:  ret
    } // end of method '<LoadAnimeLoadInfoCoroutine>d__88'::'<>m__Finally2'

    .method private hidebysig instance void 
            '<>m__Finally3'() cil managed
    {
      // 代码大小       26 (0x1a)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldc.i4.s   -4
      IL_0003:  stfld      int32 Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>1__state'
      IL_0008:  ldarg.0
      IL_0009:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>7__wrap4'
      IL_000e:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>
      IL_0014:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0019:  ret
    } // end of method '<LoadAnimeLoadInfoCoroutine>d__88'::'<>m__Finally3'

    .method private hidebysig newslot specialname virtual final 
            instance object  'System.Collections.Generic.IEnumerator<System.Object>.get_Current'() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override  method instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<object>::get_Current()
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      object Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>2__current'
      IL_0006:  ret
    } // end of method '<LoadAnimeLoadInfoCoroutine>d__88'::'System.Collections.Generic.IEnumerator<System.Object>.get_Current'

    .method private hidebysig newslot virtual final 
            instance void  System.Collections.IEnumerator.Reset() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override [mscorlib]System.Collections.IEnumerator::Reset
      // 代码大小       6 (0x6)
      .maxstack  8
      IL_0000:  newobj     instance void [mscorlib]System.NotSupportedException::.ctor()
      IL_0005:  throw
    } // end of method '<LoadAnimeLoadInfoCoroutine>d__88'::System.Collections.IEnumerator.Reset

    .method private hidebysig newslot specialname virtual final 
            instance object  System.Collections.IEnumerator.get_Current() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override [mscorlib]System.Collections.IEnumerator::get_Current
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      object Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>2__current'
      IL_0006:  ret
    } // end of method '<LoadAnimeLoadInfoCoroutine>d__88'::System.Collections.IEnumerator.get_Current

    .property instance object 'System.Collections.Generic.IEnumerator<System.Object>.Current'()
    {
      .get instance object Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'System.Collections.Generic.IEnumerator<System.Object>.get_Current'()
    } // end of property '<LoadAnimeLoadInfoCoroutine>d__88'::'System.Collections.Generic.IEnumerator<System.Object>.Current'
    .property instance object System.Collections.IEnumerator.Current()
    {
      .get instance object Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::System.Collections.IEnumerator.get_Current()
    } // end of property '<LoadAnimeLoadInfoCoroutine>d__88'::System.Collections.IEnumerator.Current
  } // end of class '<LoadAnimeLoadInfoCoroutine>d__88'

  .class auto ansi sealed nested private beforefieldinit '<LoadVoiceLoadInfoCoroutine>d__91'
         extends [mscorlib]System.Object
         implements class [mscorlib]System.Collections.Generic.IEnumerator`1<object>,
                    [mscorlib]System.Collections.IEnumerator,
                    [mscorlib]System.IDisposable
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field private int32 '<>1__state'
    .field private object '<>2__current'
    .field public class Studio.Info '<>4__this'
    .field public string _bundlePath
    .field public string _regex
    .field private string '<manifest>5__2'
    .field private valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> '<>7__wrap2'
    .field private valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> '<>7__wrap3'
    .field private valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> '<>7__wrap4'
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(int32 '<>1__state') cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       14 (0xe)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ldarg.0
      IL_0007:  ldarg.1
      IL_0008:  stfld      int32 Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>1__state'
      IL_000d:  ret
    } // end of method '<LoadVoiceLoadInfoCoroutine>d__91'::.ctor

    .method private hidebysig newslot virtual final 
            instance void  System.IDisposable.Dispose() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override [mscorlib]System.IDisposable::Dispose
      // 代码大小       69 (0x45)
      .maxstack  2
      .locals init (int32 V_0)
      IL_0000:  ldarg.0
      IL_0001:  ldfld      int32 Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>1__state'
      IL_0006:  stloc.0
      IL_0007:  ldloc.0
      IL_0008:  ldc.i4.s   -5
      IL_000a:  sub
      IL_000b:  ldc.i4.2
      IL_000c:  ble.un.s   IL_0012

      IL_000e:  ldloc.0
      IL_000f:  ldc.i4.1
      IL_0010:  bne.un.s   IL_0044

      IL_0012:  nop
      .try
      {
        IL_0013:  ldloc.0
        IL_0014:  ldc.i4.s   -5
        IL_0016:  sub
        IL_0017:  ldc.i4.1
        IL_0018:  ble.un.s   IL_0020

        IL_001a:  ldloc.0
        IL_001b:  ldc.i4.1
        IL_001c:  beq.s      IL_0020

        IL_001e:  leave.s    IL_0044

        IL_0020:  nop
        .try
        {
          IL_0021:  ldloc.0
          IL_0022:  ldc.i4.s   -5
          IL_0024:  beq.s      IL_002c

          IL_0026:  ldloc.0
          IL_0027:  ldc.i4.1
          IL_0028:  beq.s      IL_002c

          IL_002a:  leave.s    IL_0044

          IL_002c:  nop
          .try
          {
            IL_002d:  leave.s    IL_0044

          }  // end .try
          finally
          {
            IL_002f:  ldarg.0
            IL_0030:  call       instance void Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>m__Finally3'()
            IL_0035:  endfinally
          }  // end handler
        }  // end .try
        finally
        {
          IL_0036:  ldarg.0
          IL_0037:  call       instance void Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>m__Finally2'()
          IL_003c:  endfinally
        }  // end handler
      }  // end .try
      finally
      {
        IL_003d:  ldarg.0
        IL_003e:  call       instance void Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>m__Finally1'()
        IL_0043:  endfinally
      }  // end handler
      IL_0044:  ret
    } // end of method '<LoadVoiceLoadInfoCoroutine>d__91'::System.IDisposable.Dispose

    .method private hidebysig newslot virtual final 
            instance bool  MoveNext() cil managed
    {
      .override [mscorlib]System.Collections.IEnumerator::MoveNext
      // 代码大小       688 (0x2b0)
      .maxstack  5
      .locals init (bool V_0,
               int32 V_1,
               class Studio.Info V_2,
               string[] V_3,
               string V_4,
               class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> V_5,
               int32 V_6,
               int32 V_7,
               int32 V_8,
               int32 V_9,
               valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> V_10,
               valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_11,
               valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string> V_12)
      .try
      {
        IL_0000:  ldarg.0
        IL_0001:  ldfld      int32 Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>1__state'
        IL_0006:  stloc.1
        IL_0007:  ldarg.0
        IL_0008:  ldfld      class Studio.Info Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>4__this'
        IL_000d:  stloc.2
        IL_000e:  ldloc.1
        IL_000f:  brfalse.s  IL_001f

        IL_0011:  ldloc.1
        IL_0012:  ldc.i4.1
        IL_0013:  beq        IL_022d

        IL_0018:  ldc.i4.0
        IL_0019:  stloc.0
        IL_001a:  leave      IL_02ae

        IL_001f:  ldarg.0
        IL_0020:  ldc.i4.m1
        IL_0021:  stfld      int32 Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>1__state'
        IL_0026:  ldarg.0
        IL_0027:  ldstr      ""
        IL_002c:  stfld      string Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<manifest>5__2'
        IL_0031:  ldloc.2
        IL_0032:  ldarg.0
        IL_0033:  ldfld      string Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::_bundlePath
        IL_0038:  ldarg.0
        IL_0039:  ldfld      string Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::_regex
        IL_003e:  ldarg.0
        IL_003f:  ldflda     string Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<manifest>5__2'
        IL_0044:  call       instance string[] Studio.Info::FindAllAssetName(string,
                                                                             string,
                                                                             string&)
        IL_0049:  stloc.3
        IL_004a:  ldloc.3
        IL_004b:  call       bool [IL]NullCheck::IsNullOrEmpty<string>(class [mscorlib]System.Collections.Generic.IReadOnlyCollection`1<!!0>)
        IL_0050:  brfalse.s  IL_0059

        IL_0052:  ldc.i4.0
        IL_0053:  stloc.0
        IL_0054:  leave      IL_02ae

        IL_0059:  ldarg.0
        IL_005a:  ldfld      string Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::_regex
        IL_005f:  ldc.i4.1
        IL_0060:  newarr     [mscorlib]System.Char
        IL_0065:  dup
        IL_0066:  ldc.i4.0
        IL_0067:  ldc.i4.s   95
        IL_0069:  stelem.i2
        IL_006a:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
        IL_006f:  ldc.i4.0
        IL_0070:  ldelem.ref
        IL_0071:  callvirt   instance string [mscorlib]System.String::ToLower()
        IL_0076:  stloc.s    V_4
        IL_0078:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::.ctor()
        IL_007d:  stloc.s    V_5
        IL_007f:  ldc.i4.0
        IL_0080:  stloc.s    V_6
        IL_0082:  br         IL_0166

        IL_0087:  ldloc.3
        IL_0088:  ldloc.s    V_6
        IL_008a:  ldelem.ref
        IL_008b:  ldc.i4.1
        IL_008c:  newarr     [mscorlib]System.Char
        IL_0091:  dup
        IL_0092:  ldc.i4.0
        IL_0093:  ldc.i4.s   95
        IL_0095:  stelem.i2
        IL_0096:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
        IL_009b:  ldc.i4.0
        IL_009c:  ldelem.ref
        IL_009d:  callvirt   instance string [mscorlib]System.String::ToLower()
        IL_00a2:  ldloc.s    V_4
        IL_00a4:  callvirt   instance int32 [mscorlib]System.String::CompareTo(string)
        IL_00a9:  brtrue     IL_0160

        IL_00ae:  ldloc.3
        IL_00af:  ldloc.s    V_6
        IL_00b1:  ldelem.ref
        IL_00b2:  ldarg.0
        IL_00b3:  ldfld      string Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::_regex
        IL_00b8:  ldc.i4.1
        IL_00b9:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                    string,
                                                                                                                                    valuetype [System]System.Text.RegularExpressions.RegexOptions)
        IL_00be:  dup
        IL_00bf:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
        IL_00c4:  ldc.i4.1
        IL_00c5:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
        IL_00ca:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
        IL_00cf:  call       int32 [mscorlib]System.Int32::Parse(string)
        IL_00d4:  stloc.s    V_7
        IL_00d6:  dup
        IL_00d7:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
        IL_00dc:  ldc.i4.2
        IL_00dd:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
        IL_00e2:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
        IL_00e7:  call       int32 [mscorlib]System.Int32::Parse(string)
        IL_00ec:  stloc.s    V_8
        IL_00ee:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
        IL_00f3:  ldc.i4.3
        IL_00f4:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
        IL_00f9:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
        IL_00fe:  call       int32 [mscorlib]System.Int32::Parse(string)
        IL_0103:  stloc.s    V_9
        IL_0105:  ldloc.s    V_5
        IL_0107:  ldloc.s    V_7
        IL_0109:  callvirt   instance bool class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::ContainsKey(!0)
        IL_010e:  brtrue.s   IL_011e

        IL_0110:  ldloc.s    V_5
        IL_0112:  ldloc.s    V_7
        IL_0114:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::.ctor()
        IL_0119:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::Add(!0,
                                                                                                                                                                                                                                                                !1)
        IL_011e:  ldloc.s    V_5
        IL_0120:  ldloc.s    V_7
        IL_0122:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Item(!0)
        IL_0127:  ldloc.s    V_8
        IL_0129:  callvirt   instance bool class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::ContainsKey(!0)
        IL_012e:  brtrue.s   IL_0145

        IL_0130:  ldloc.s    V_5
        IL_0132:  ldloc.s    V_7
        IL_0134:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Item(!0)
        IL_0139:  ldloc.s    V_8
        IL_013b:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::.ctor()
        IL_0140:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::Add(!0,
                                                                                                                                                                                             !1)
        IL_0145:  ldloc.s    V_5
        IL_0147:  ldloc.s    V_7
        IL_0149:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Item(!0)
        IL_014e:  ldloc.s    V_8
        IL_0150:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Item(!0)
        IL_0155:  ldloc.s    V_9
        IL_0157:  ldloc.3
        IL_0158:  ldloc.s    V_6
        IL_015a:  ldelem.ref
        IL_015b:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::Add(!0,
                                                                                                                          !1)
        IL_0160:  ldloc.s    V_6
        IL_0162:  ldc.i4.1
        IL_0163:  add
        IL_0164:  stloc.s    V_6
        IL_0166:  ldloc.s    V_6
        IL_0168:  ldloc.3
        IL_0169:  ldlen
        IL_016a:  conv.i4
        IL_016b:  blt        IL_0087

        IL_0170:  ldarg.0
        IL_0171:  ldloc.s    V_5
        IL_0173:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::GetEnumerator()
        IL_0178:  stfld      valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap2'
        IL_017d:  ldarg.0
        IL_017e:  ldc.i4.s   -3
        IL_0180:  stfld      int32 Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>1__state'
        IL_0185:  br         IL_0281

        IL_018a:  ldarg.0
        IL_018b:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap2'
        IL_0190:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Current()
        IL_0195:  stloc.s    V_10
        IL_0197:  ldarg.0
        IL_0198:  ldloca.s   V_10
        IL_019a:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::get_Value()
        IL_019f:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::GetEnumerator()
        IL_01a4:  stfld      valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap3'
        IL_01a9:  ldarg.0
        IL_01aa:  ldc.i4.s   -4
        IL_01ac:  stfld      int32 Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>1__state'
        IL_01b1:  br         IL_025f

        IL_01b6:  ldarg.0
        IL_01b7:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap3'
        IL_01bc:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Current()
        IL_01c1:  stloc.s    V_11
        IL_01c3:  ldarg.0
        IL_01c4:  ldloca.s   V_11
        IL_01c6:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Value()
        IL_01cb:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::GetEnumerator()
        IL_01d0:  stfld      valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap4'
        IL_01d5:  ldarg.0
        IL_01d6:  ldc.i4.s   -5
        IL_01d8:  stfld      int32 Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>1__state'
        IL_01dd:  br.s       IL_0240

        IL_01df:  ldarg.0
        IL_01e0:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap4'
        IL_01e5:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::get_Current()
        IL_01ea:  stloc.s    V_12
        IL_01ec:  ldloc.2
        IL_01ed:  ldloc.2
        IL_01ee:  ldarg.0
        IL_01ef:  ldfld      string Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::_bundlePath
        IL_01f4:  ldloca.s   V_12
        IL_01f6:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string>::get_Value()
        IL_01fb:  ldarg.0
        IL_01fc:  ldfld      string Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<manifest>5__2'
        IL_0201:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                     string,
                                                                                     string)
        IL_0206:  call       instance void Studio.Info::LoadVoiceLoadInfo(class [IL]ExcelData)
        IL_020b:  ldloc.2
        IL_020c:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
        IL_0211:  callvirt   instance bool Studio.Info/WaitTime::get_isOver()
        IL_0216:  brfalse.s  IL_0240

        IL_0218:  ldarg.0
        IL_0219:  ldnull
        IL_021a:  stfld      object Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>2__current'
        IL_021f:  ldarg.0
        IL_0220:  ldc.i4.1
        IL_0221:  stfld      int32 Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>1__state'
        IL_0226:  ldc.i4.1
        IL_0227:  stloc.0
        IL_0228:  leave      IL_02ae

        IL_022d:  ldarg.0
        IL_022e:  ldc.i4.s   -5
        IL_0230:  stfld      int32 Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>1__state'
        IL_0235:  ldloc.2
        IL_0236:  ldfld      class Studio.Info/WaitTime Studio.Info::waitTime
        IL_023b:  callvirt   instance void Studio.Info/WaitTime::Next()
        IL_0240:  ldarg.0
        IL_0241:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap4'
        IL_0246:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::MoveNext()
        IL_024b:  brtrue.s   IL_01df

        IL_024d:  ldarg.0
        IL_024e:  call       instance void Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>m__Finally3'()
        IL_0253:  ldarg.0
        IL_0254:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap4'
        IL_0259:  initobj    valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>
        IL_025f:  ldarg.0
        IL_0260:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap3'
        IL_0265:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::MoveNext()
        IL_026a:  brtrue     IL_01b6

        IL_026f:  ldarg.0
        IL_0270:  call       instance void Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>m__Finally2'()
        IL_0275:  ldarg.0
        IL_0276:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap3'
        IL_027b:  initobj    valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>
        IL_0281:  ldarg.0
        IL_0282:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap2'
        IL_0287:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>::MoveNext()
        IL_028c:  brtrue     IL_018a

        IL_0291:  ldarg.0
        IL_0292:  call       instance void Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>m__Finally1'()
        IL_0297:  ldarg.0
        IL_0298:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap2'
        IL_029d:  initobj    valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>
        IL_02a3:  ldc.i4.0
        IL_02a4:  stloc.0
        IL_02a5:  leave.s    IL_02ae

      }  // end .try
      fault
      {
        IL_02a7:  ldarg.0
        IL_02a8:  call       instance void Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::System.IDisposable.Dispose()
        IL_02ad:  endfinally
      }  // end handler
      IL_02ae:  ldloc.0
      IL_02af:  ret
    } // end of method '<LoadVoiceLoadInfoCoroutine>d__91'::MoveNext

    .method private hidebysig instance void 
            '<>m__Finally1'() cil managed
    {
      // 代码大小       25 (0x19)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldc.i4.m1
      IL_0002:  stfld      int32 Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>1__state'
      IL_0007:  ldarg.0
      IL_0008:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap2'
      IL_000d:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>>
      IL_0013:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0018:  ret
    } // end of method '<LoadVoiceLoadInfoCoroutine>d__91'::'<>m__Finally1'

    .method private hidebysig instance void 
            '<>m__Finally2'() cil managed
    {
      // 代码大小       26 (0x1a)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldc.i4.s   -3
      IL_0003:  stfld      int32 Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>1__state'
      IL_0008:  ldarg.0
      IL_0009:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap3'
      IL_000e:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>
      IL_0014:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0019:  ret
    } // end of method '<LoadVoiceLoadInfoCoroutine>d__91'::'<>m__Finally2'

    .method private hidebysig instance void 
            '<>m__Finally3'() cil managed
    {
      // 代码大小       26 (0x1a)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldc.i4.s   -4
      IL_0003:  stfld      int32 Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>1__state'
      IL_0008:  ldarg.0
      IL_0009:  ldflda     valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>7__wrap4'
      IL_000e:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>
      IL_0014:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0019:  ret
    } // end of method '<LoadVoiceLoadInfoCoroutine>d__91'::'<>m__Finally3'

    .method private hidebysig newslot specialname virtual final 
            instance object  'System.Collections.Generic.IEnumerator<System.Object>.get_Current'() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override  method instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<object>::get_Current()
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      object Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>2__current'
      IL_0006:  ret
    } // end of method '<LoadVoiceLoadInfoCoroutine>d__91'::'System.Collections.Generic.IEnumerator<System.Object>.get_Current'

    .method private hidebysig newslot virtual final 
            instance void  System.Collections.IEnumerator.Reset() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override [mscorlib]System.Collections.IEnumerator::Reset
      // 代码大小       6 (0x6)
      .maxstack  8
      IL_0000:  newobj     instance void [mscorlib]System.NotSupportedException::.ctor()
      IL_0005:  throw
    } // end of method '<LoadVoiceLoadInfoCoroutine>d__91'::System.Collections.IEnumerator.Reset

    .method private hidebysig newslot specialname virtual final 
            instance object  System.Collections.IEnumerator.get_Current() cil managed
    {
      .custom instance void [mscorlib]System.Diagnostics.DebuggerHiddenAttribute::.ctor() = ( 01 00 00 00 ) 
      .override [mscorlib]System.Collections.IEnumerator::get_Current
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      object Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>2__current'
      IL_0006:  ret
    } // end of method '<LoadVoiceLoadInfoCoroutine>d__91'::System.Collections.IEnumerator.get_Current

    .property instance object 'System.Collections.Generic.IEnumerator<System.Object>.Current'()
    {
      .get instance object Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'System.Collections.Generic.IEnumerator<System.Object>.get_Current'()
    } // end of property '<LoadVoiceLoadInfoCoroutine>d__91'::'System.Collections.Generic.IEnumerator<System.Object>.Current'
    .property instance object System.Collections.IEnumerator.Current()
    {
      .get instance object Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::System.Collections.IEnumerator.get_Current()
    } // end of property '<LoadVoiceLoadInfoCoroutine>d__91'::System.Collections.IEnumerator.Current
  } // end of class '<LoadVoiceLoadInfoCoroutine>d__91'

  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/BoneInfo> dicBoneInfo
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> dicItemGroupCategory
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>> dicItemLoadInfo
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>> dicItemColorData
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AccessoryGroupInfo> dicAccessoryGroup
  .field private int32 '<AccessoryPointNum>k__BackingField'
  .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
  .field private class [IL]ExcelData m_AccessoryPointGroup
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LightLoadInfo> dicLightLoadInfo
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> dicAGroupCategory
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> dicAnimeLoadInfo
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> dicVoiceGroupCategory
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>> dicVoiceLoadInfo
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> dicBGMLoadInfo
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> dicENVLoadInfo
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/MapLoadInfo> dicMapLoadInfo
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> dicColorGradingLoadInfo
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> dicReflectionProbeLoadInfo
  .field public class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/SkyPatternInfo> dicSkyPatternInfo
  .field private class Studio.Info/FileCheck fileCheck
  .field private bool '<isLoadList>k__BackingField'
  .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
  .field private class Studio.Info/WaitTime waitTime
  .field private bool '<IsInstallAI>k__BackingField'
  .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
  .field private bool '<IsInstallAdd>k__BackingField'
  .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
  .method public hidebysig specialname instance int32 
          get_AccessoryPointNum() cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    // 代码大小       7 (0x7)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldfld      int32 Studio.Info::'<AccessoryPointNum>k__BackingField'
    IL_0006:  ret
  } // end of method Info::get_AccessoryPointNum

  .method private hidebysig specialname instance void 
          set_AccessoryPointNum(int32 'value') cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    // 代码大小       8 (0x8)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldarg.1
    IL_0002:  stfld      int32 Studio.Info::'<AccessoryPointNum>k__BackingField'
    IL_0007:  ret
  } // end of method Info::set_AccessoryPointNum

  .method public hidebysig specialname instance int32[] 
          get_AccessoryPointsIndex() cil managed
  {
    // 代码大小       116 (0x74)
    .maxstack  5
    .locals init (class [System.Core]System.Collections.Generic.HashSet`1<int32> V_0,
             valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.Info/AccessoryGroupInfo> V_1,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/AccessoryGroupInfo> V_2)
    IL_0000:  newobj     instance void class [System.Core]System.Collections.Generic.HashSet`1<int32>::.ctor()
    IL_0005:  stloc.0
    IL_0006:  ldarg.0
    IL_0007:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AccessoryGroupInfo> Studio.Info::dicAccessoryGroup
    IL_000c:  callvirt   instance valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<!0,!1> class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AccessoryGroupInfo>::GetEnumerator()
    IL_0011:  stloc.1
    .try
    {
      IL_0012:  br.s       IL_0054

      IL_0014:  ldloca.s   V_1
      IL_0016:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.Info/AccessoryGroupInfo>::get_Current()
      IL_001b:  stloc.2
      IL_001c:  ldloc.0
      IL_001d:  ldloca.s   V_2
      IL_001f:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/AccessoryGroupInfo>::get_Value()
      IL_0024:  callvirt   instance int32[] Studio.Info/AccessoryGroupInfo::get_Targets()
      IL_0029:  ldc.i4.0
      IL_002a:  ldelem.i4
      IL_002b:  ldloca.s   V_2
      IL_002d:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/AccessoryGroupInfo>::get_Value()
      IL_0032:  callvirt   instance int32[] Studio.Info/AccessoryGroupInfo::get_Targets()
      IL_0037:  ldc.i4.1
      IL_0038:  ldelem.i4
      IL_0039:  ldloca.s   V_2
      IL_003b:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/AccessoryGroupInfo>::get_Value()
      IL_0040:  callvirt   instance int32[] Studio.Info/AccessoryGroupInfo::get_Targets()
      IL_0045:  ldc.i4.0
      IL_0046:  ldelem.i4
      IL_0047:  sub
      IL_0048:  ldc.i4.1
      IL_0049:  add
      IL_004a:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<int32> [System.Core]System.Linq.Enumerable::Range(int32,
                                                                                                                                      int32)
      IL_004f:  callvirt   instance void class [System.Core]System.Collections.Generic.HashSet`1<int32>::UnionWith(class [mscorlib]System.Collections.Generic.IEnumerable`1<!0>)
      IL_0054:  ldloca.s   V_1
      IL_0056:  call       instance bool valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.Info/AccessoryGroupInfo>::MoveNext()
      IL_005b:  brtrue.s   IL_0014

      IL_005d:  leave.s    IL_006d

    }  // end .try
    finally
    {
      IL_005f:  ldloca.s   V_1
      IL_0061:  constrained. valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.Info/AccessoryGroupInfo>
      IL_0067:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_006c:  endfinally
    }  // end handler
    IL_006d:  ldloc.0
    IL_006e:  call       !!0[] [System.Core]System.Linq.Enumerable::ToArray<int32>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>)
    IL_0073:  ret
  } // end of method Info::get_AccessoryPointsIndex

  .method public hidebysig specialname instance class [IL]ExcelData 
          get_accessoryPointGroup() cil managed
  {
    // 代码大小       7 (0x7)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldfld      class [IL]ExcelData Studio.Info::m_AccessoryPointGroup
    IL_0006:  ret
  } // end of method Info::get_accessoryPointGroup

  .method public hidebysig specialname instance bool 
          get_isLoadList() cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    // 代码大小       7 (0x7)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldfld      bool Studio.Info::'<isLoadList>k__BackingField'
    IL_0006:  ret
  } // end of method Info::get_isLoadList

  .method private hidebysig specialname instance void 
          set_isLoadList(bool 'value') cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    // 代码大小       8 (0x8)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldarg.1
    IL_0002:  stfld      bool Studio.Info::'<isLoadList>k__BackingField'
    IL_0007:  ret
  } // end of method Info::set_isLoadList

  .method public hidebysig specialname instance bool 
          get_IsInstallAI() cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    // 代码大小       7 (0x7)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldfld      bool Studio.Info::'<IsInstallAI>k__BackingField'
    IL_0006:  ret
  } // end of method Info::get_IsInstallAI

  .method private hidebysig specialname instance void 
          set_IsInstallAI(bool 'value') cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    // 代码大小       8 (0x8)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldarg.1
    IL_0002:  stfld      bool Studio.Info::'<IsInstallAI>k__BackingField'
    IL_0007:  ret
  } // end of method Info::set_IsInstallAI

  .method private hidebysig instance void 
          CheckIsAI() cil managed
  {
    // 代码大小       88 (0x58)
    .maxstack  5
    .locals init (string V_0,
             string V_1)
    IL_0000:  ldstr      "Software\\illusion\\AI-Syoujyo\\AI-Syoujyo"
    IL_0005:  stloc.0
    IL_0006:  ldloc.0
    IL_0007:  ldstr      "HKEY_CURRENT_USER"
    IL_000c:  call       bool [IL]YS_Assist::IsRegistryKey(string,
                                                           string)
    IL_0011:  brfalse.s  IL_0057

    IL_0013:  ldloc.0
    IL_0014:  ldstr      "InstallDir"
    IL_0019:  ldstr      "HKEY_CURRENT_USER"
    IL_001e:  call       string [IL]YS_Assist::GetRegistryInfoFrom(string,
                                                                   string,
                                                                   string)
    IL_0023:  stloc.1
    IL_0024:  ldloc.1
    IL_0025:  call       bool [IL]NullCheck::IsNullOrEmpty(string)
    IL_002a:  brtrue.s   IL_0057

    IL_002c:  ldloc.1
    IL_002d:  ldc.i4.1
    IL_002e:  newarr     [mscorlib]System.Char
    IL_0033:  dup
    IL_0034:  ldc.i4.0
    IL_0035:  ldc.i4.s   92
    IL_0037:  stelem.i2
    IL_0038:  callvirt   instance string [mscorlib]System.String::TrimEnd(char[])
    IL_003d:  stloc.1
    IL_003e:  ldloc.1
    IL_003f:  ldstr      "/AI-Syoujyo.exe"
    IL_0044:  call       string [mscorlib]System.String::Concat(string,
                                                                string)
    IL_0049:  call       bool [mscorlib]System.IO.File::Exists(string)
    IL_004e:  brfalse.s  IL_0057

    IL_0050:  ldarg.0
    IL_0051:  ldc.i4.1
    IL_0052:  call       instance void Studio.Info::set_IsInstallAI(bool)
    IL_0057:  ret
  } // end of method Info::CheckIsAI

  .method public hidebysig specialname instance bool 
          get_IsInstallAdd() cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    // 代码大小       7 (0x7)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldfld      bool Studio.Info::'<IsInstallAdd>k__BackingField'
    IL_0006:  ret
  } // end of method Info::get_IsInstallAdd

  .method private hidebysig specialname instance void 
          set_IsInstallAdd(bool 'value') cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    // 代码大小       8 (0x8)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldarg.1
    IL_0002:  stfld      bool Studio.Info::'<IsInstallAdd>k__BackingField'
    IL_0007:  ret
  } // end of method Info::set_IsInstallAdd

  .method private hidebysig instance void 
          CheckIsAdd() cil managed
  {
    // 代码大小       17 (0x11)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldstr      "add50"
    IL_0006:  call       bool Studio.AssetBundleCheck::IsManifest(string)
    IL_000b:  call       instance void Studio.Info::set_IsInstallAdd(bool)
    IL_0010:  ret
  } // end of method Info::CheckIsAdd

  .method public hidebysig instance class [mscorlib]System.Collections.IEnumerator 
          LoadExcelDataCoroutine() cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.IteratorStateMachineAttribute::.ctor(class [mscorlib]System.Type) = ( 01 00 29 53 74 75 64 69 6F 2E 49 6E 66 6F 2B 3C   // ..)Studio.Info+<
                                                                                                                                          4C 6F 61 64 45 78 63 65 6C 44 61 74 61 43 6F 72   // LoadExcelDataCor
                                                                                                                                          6F 75 74 69 6E 65 3E 64 5F 5F 35 38 00 00 )       // outine>d__58..
    // 代码大小       14 (0xe)
    .maxstack  8
    IL_0000:  ldc.i4.0
    IL_0001:  newobj     instance void Studio.Info/'<LoadExcelDataCoroutine>d__58'::.ctor(int32)
    IL_0006:  dup
    IL_0007:  ldarg.0
    IL_0008:  stfld      class Studio.Info Studio.Info/'<LoadExcelDataCoroutine>d__58'::'<>4__this'
    IL_000d:  ret
  } // end of method Info::LoadExcelDataCoroutine

  .method public hidebysig instance class Studio.Info/LoadCommonInfo 
          GetVoiceInfo(int32 _group,
                       int32 _category,
                       int32 _no) cil managed
  {
    // 代码大小       52 (0x34)
    .maxstack  3
    .locals init (class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>> V_0,
             class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> V_1,
             class Studio.Info/LoadCommonInfo V_2)
    IL_0000:  ldnull
    IL_0001:  stloc.0
    IL_0002:  ldarg.0
    IL_0003:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>> Studio.Info::dicVoiceLoadInfo
    IL_0008:  ldarg.1
    IL_0009:  ldloca.s   V_0
    IL_000b:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>>::TryGetValue(!0,
                                                                                                                                                                                                                                                                                  !1&)
    IL_0010:  brtrue.s   IL_0014

    IL_0012:  ldnull
    IL_0013:  ret

    IL_0014:  ldnull
    IL_0015:  stloc.1
    IL_0016:  ldloc.0
    IL_0017:  ldarg.2
    IL_0018:  ldloca.s   V_1
    IL_001a:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>::TryGetValue(!0,
                                                                                                                                                                                                                   !1&)
    IL_001f:  brtrue.s   IL_0023

    IL_0021:  ldnull
    IL_0022:  ret

    IL_0023:  ldnull
    IL_0024:  stloc.2
    IL_0025:  ldloc.1
    IL_0026:  ldarg.3
    IL_0027:  ldloca.s   V_2
    IL_0029:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>::TryGetValue(!0,
                                                                                                                                                    !1&)
    IL_002e:  brtrue.s   IL_0032

    IL_0030:  ldnull
    IL_0031:  ret

    IL_0032:  ldloc.2
    IL_0033:  ret
  } // end of method Info::GetVoiceInfo

  .method public hidebysig instance class Studio.ItemColorData/ColorData 
          SafeGetItemColorData(int32 _group,
                               int32 _category,
                               int32 _id) cil managed
  {
    // 代码大小       52 (0x34)
    .maxstack  3
    .locals init (class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>> V_0,
             class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData> V_1,
             class Studio.ItemColorData/ColorData V_2)
    IL_0000:  ldnull
    IL_0001:  stloc.0
    IL_0002:  ldarg.0
    IL_0003:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>> Studio.Info::dicItemColorData
    IL_0008:  ldarg.1
    IL_0009:  ldloca.s   V_0
    IL_000b:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>>::TryGetValue(!0,
                                                                                                                                                                                                                                                                                      !1&)
    IL_0010:  brtrue.s   IL_0014

    IL_0012:  ldnull
    IL_0013:  ret

    IL_0014:  ldnull
    IL_0015:  stloc.1
    IL_0016:  ldloc.0
    IL_0017:  ldarg.2
    IL_0018:  ldloca.s   V_1
    IL_001a:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>::TryGetValue(!0,
                                                                                                                                                                                                                       !1&)
    IL_001f:  brtrue.s   IL_0023

    IL_0021:  ldnull
    IL_0022:  ret

    IL_0023:  ldnull
    IL_0024:  stloc.2
    IL_0025:  ldloc.1
    IL_0026:  ldarg.3
    IL_0027:  ldloca.s   V_2
    IL_0029:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>::TryGetValue(!0,
                                                                                                                                                        !1&)
    IL_002e:  brtrue.s   IL_0032

    IL_0030:  ldnull
    IL_0031:  ret

    IL_0032:  ldloc.2
    IL_0033:  ret
  } // end of method Info::SafeGetItemColorData

  .method public hidebysig instance bool 
          ExistItemGroup(int32 _group) cil managed
  {
    // 代码大小       61 (0x3d)
    .maxstack  3
    .locals init (class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>> V_0)
    IL_0000:  ldnull
    IL_0001:  stloc.0
    IL_0002:  ldarg.0
    IL_0003:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>> Studio.Info::dicItemLoadInfo
    IL_0008:  ldarg.1
    IL_0009:  ldloca.s   V_0
    IL_000b:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>>::TryGetValue(!0,
                                                                                                                                                                                                                                                                                !1&)
    IL_0010:  brtrue.s   IL_0014

    IL_0012:  ldc.i4.0
    IL_0013:  ret

    IL_0014:  ldloc.0
    IL_0015:  ldsfld     class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>,int32> Studio.Info/'<>c'::'<>9__61_0'
    IL_001a:  dup
    IL_001b:  brtrue.s   IL_0034

    IL_001d:  pop
    IL_001e:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0023:  ldftn      instance int32 Studio.Info/'<>c'::'<ExistItemGroup>b__61_0'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>)
    IL_0029:  newobj     instance void class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>,int32>::.ctor(object,
                                                                                                                                                                                                                                                      native int)
    IL_002e:  dup
    IL_002f:  stsfld     class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>,int32> Studio.Info/'<>c'::'<>9__61_0'
    IL_0034:  call       int32 [System.Core]System.Linq.Enumerable::Sum<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                                            class [mscorlib]System.Func`2<!!0,int32>)
    IL_0039:  ldc.i4.0
    IL_003a:  cgt.un
    IL_003c:  ret
  } // end of method Info::ExistItemGroup

  .method public hidebysig instance bool 
          ExistItemCategory(int32 _group,
                            int32 _category) cil managed
  {
    // 代码大小       45 (0x2d)
    .maxstack  3
    .locals init (class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>> V_0,
             class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo> V_1)
    IL_0000:  ldnull
    IL_0001:  stloc.0
    IL_0002:  ldarg.0
    IL_0003:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>> Studio.Info::dicItemLoadInfo
    IL_0008:  ldarg.1
    IL_0009:  ldloca.s   V_0
    IL_000b:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>>::TryGetValue(!0,
                                                                                                                                                                                                                                                                                !1&)
    IL_0010:  brtrue.s   IL_0014

    IL_0012:  ldc.i4.0
    IL_0013:  ret

    IL_0014:  ldnull
    IL_0015:  stloc.1
    IL_0016:  ldloc.0
    IL_0017:  ldarg.2
    IL_0018:  ldloca.s   V_1
    IL_001a:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>::TryGetValue(!0,
                                                                                                                                                                                                                 !1&)
    IL_001f:  brtrue.s   IL_0023

    IL_0021:  ldc.i4.0
    IL_0022:  ret

    IL_0023:  ldloc.1
    IL_0024:  callvirt   instance int32 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>::get_Count()
    IL_0029:  ldc.i4.0
    IL_002a:  cgt.un
    IL_002c:  ret
  } // end of method Info::ExistItemCategory

  .method public hidebysig instance bool 
          ExistAnimeGroup(int32 _group) cil managed
  {
    // 代码大小       61 (0x3d)
    .maxstack  3
    .locals init (class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>> V_0)
    IL_0000:  ldnull
    IL_0001:  stloc.0
    IL_0002:  ldarg.0
    IL_0003:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> Studio.Info::dicAnimeLoadInfo
    IL_0008:  ldarg.1
    IL_0009:  ldloca.s   V_0
    IL_000b:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::TryGetValue(!0,
                                                                                                                                                                                                                                                                                 !1&)
    IL_0010:  brtrue.s   IL_0014

    IL_0012:  ldc.i4.0
    IL_0013:  ret

    IL_0014:  ldloc.0
    IL_0015:  ldsfld     class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>,int32> Studio.Info/'<>c'::'<>9__63_0'
    IL_001a:  dup
    IL_001b:  brtrue.s   IL_0034

    IL_001d:  pop
    IL_001e:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0023:  ldftn      instance int32 Studio.Info/'<>c'::'<ExistAnimeGroup>b__63_0'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>)
    IL_0029:  newobj     instance void class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>,int32>::.ctor(object,
                                                                                                                                                                                                                                                       native int)
    IL_002e:  dup
    IL_002f:  stsfld     class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>,int32> Studio.Info/'<>c'::'<>9__63_0'
    IL_0034:  call       int32 [System.Core]System.Linq.Enumerable::Sum<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                                             class [mscorlib]System.Func`2<!!0,int32>)
    IL_0039:  ldc.i4.0
    IL_003a:  cgt.un
    IL_003c:  ret
  } // end of method Info::ExistAnimeGroup

  .method public hidebysig instance bool 
          ExistAnimeCategory(int32 _group,
                             int32 _category) cil managed
  {
    // 代码大小       45 (0x2d)
    .maxstack  3
    .locals init (class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>> V_0,
             class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo> V_1)
    IL_0000:  ldnull
    IL_0001:  stloc.0
    IL_0002:  ldarg.0
    IL_0003:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> Studio.Info::dicAnimeLoadInfo
    IL_0008:  ldarg.1
    IL_0009:  ldloca.s   V_0
    IL_000b:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::TryGetValue(!0,
                                                                                                                                                                                                                                                                                 !1&)
    IL_0010:  brtrue.s   IL_0014

    IL_0012:  ldc.i4.0
    IL_0013:  ret

    IL_0014:  ldnull
    IL_0015:  stloc.1
    IL_0016:  ldloc.0
    IL_0017:  ldarg.2
    IL_0018:  ldloca.s   V_1
    IL_001a:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>::TryGetValue(!0,
                                                                                                                                                                                                                  !1&)
    IL_001f:  brtrue.s   IL_0023

    IL_0021:  ldc.i4.0
    IL_0022:  ret

    IL_0023:  ldloc.1
    IL_0024:  callvirt   instance int32 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>::get_Count()
    IL_0029:  ldc.i4.0
    IL_002a:  cgt.un
    IL_002c:  ret
  } // end of method Info::ExistAnimeCategory

  .method private hidebysig instance class [IL]ExcelData 
          LoadExcelData(string _bundlePath,
                        string _fileName,
                        string _manifest) cil managed
  {
    // 代码大小       29 (0x1d)
    .maxstack  8
    IL_0000:  call       bool Studio.AssetBundleCheck::get_IsSimulation()
    IL_0005:  brfalse.s  IL_0013

    IL_0007:  ldarg.1
    IL_0008:  ldarg.2
    IL_0009:  ldc.i4.0
    IL_000a:  call       bool Studio.AssetBundleCheck::FindFile(string,
                                                                string,
                                                                bool)
    IL_000f:  brtrue.s   IL_0013

    IL_0011:  ldnull
    IL_0012:  ret

    IL_0013:  ldarg.1
    IL_0014:  ldarg.2
    IL_0015:  ldc.i4.0
    IL_0016:  ldarg.3
    IL_0017:  call       !!0 CommonLib::LoadAsset<class [IL]ExcelData>(string,
                                                                       string,
                                                                       bool,
                                                                       string)
    IL_001c:  ret
  } // end of method Info::LoadExcelData

  .method private hidebysig instance class [IL]ExcelData 
          LoadExcelDataFromBundle(string _bundlePath,
                                  string _fileName,
                                  string _manifest) cil managed
  {
    // 代码大小       10 (0xa)
    .maxstack  8
    IL_0000:  ldarg.1
    IL_0001:  ldarg.2
    IL_0002:  ldc.i4.0
    IL_0003:  ldarg.3
    IL_0004:  call       !!0 Studio.AddObjectAssist::LoadAsset<class [IL]ExcelData>(string,
                                                                                    string,
                                                                                    bool,
                                                                                    string)
    IL_0009:  ret
  } // end of method Info::LoadExcelDataFromBundle

  .method private hidebysig instance string[] 
          FindAllAssetName(string _bundlePath,
                           string _regex,
                           [out] string& _manifest) cil managed
  {
    // 代码大小       314 (0x13a)
    .maxstack  4
    .locals init (class Studio.Info/'<>c__DisplayClass67_0' V_0,
             string[] V_1,
             class [mscorlib]System.Collections.Generic.IEnumerator`1<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>> V_2,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack> V_3,
             class LoadedAssetBundle V_4,
             class [mscorlib]System.Func`2<string,bool> V_5,
             string[] V_6)
    IL_0000:  newobj     instance void Studio.Info/'<>c__DisplayClass67_0'::.ctor()
    IL_0005:  stloc.0
    IL_0006:  ldloc.0
    IL_0007:  ldarg.2
    IL_0008:  stfld      string Studio.Info/'<>c__DisplayClass67_0'::_regex
    IL_000d:  ldnull
    IL_000e:  stloc.1
    IL_000f:  call       bool Studio.AssetBundleCheck::get_IsSimulation()
    IL_0014:  brfalse.s  IL_002a

    IL_0016:  ldarg.1
    IL_0017:  ldloc.0
    IL_0018:  ldfld      string Studio.Info/'<>c__DisplayClass67_0'::_regex
    IL_001d:  ldc.i4.0
    IL_001e:  ldc.i4.1
    IL_001f:  call       string[] Studio.AssetBundleCheck::FindAllAssetName(string,
                                                                            string,
                                                                            bool,
                                                                            valuetype [System]System.Text.RegularExpressions.RegexOptions)
    IL_0024:  stloc.1
    IL_0025:  br         IL_012e

    IL_002a:  call       class [mscorlib]System.Collections.Generic.Dictionary`2<string,class AssetBundleManager/BundlePack> AssetBundleManager::get_ManifestBundlePack()
    IL_002f:  ldsfld     class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool> Studio.Info/'<>c'::'<>9__67_0'
    IL_0034:  dup
    IL_0035:  brtrue.s   IL_004e

    IL_0037:  pop
    IL_0038:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_003d:  ldftn      instance bool Studio.Info/'<>c'::'<FindAllAssetName>b__67_0'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>)
    IL_0043:  newobj     instance void class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool>::.ctor(object,
                                                                                                                                                                                            native int)
    IL_0048:  dup
    IL_0049:  stsfld     class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool> Studio.Info/'<>c'::'<>9__67_0'
    IL_004e:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Where<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                                             class [mscorlib]System.Func`2<!!0,bool>)
    IL_0053:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>::GetEnumerator()
    IL_0058:  stloc.2
    .try
    {
      IL_0059:  br         IL_0117

      IL_005e:  ldloc.2
      IL_005f:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>::get_Current()
      IL_0064:  stloc.3
      IL_0065:  ldloca.s   V_3
      IL_0067:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Value()
      IL_006c:  callvirt   instance class [UnityEngine.AssetBundleModule]UnityEngine.AssetBundleManifest AssetBundleManager/BundlePack::get_AssetBundleManifest()
      IL_0071:  callvirt   instance string[] [UnityEngine.AssetBundleModule]UnityEngine.AssetBundleManifest::GetAllAssetBundles()
      IL_0076:  ldarg.1
      IL_0077:  call       bool [System.Core]System.Linq.Enumerable::Contains<string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                      !!0)
      IL_007c:  brfalse    IL_0117

      IL_0081:  ldnull
      IL_0082:  stloc.s    V_4
      IL_0084:  ldloca.s   V_3
      IL_0086:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Value()
      IL_008b:  callvirt   instance class [mscorlib]System.Collections.Generic.Dictionary`2<string,class LoadedAssetBundle> AssetBundleManager/BundlePack::get_LoadedAssetBundles()
      IL_0090:  ldarg.1
      IL_0091:  ldloca.s   V_4
      IL_0093:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<string,class LoadedAssetBundle>::TryGetValue(!0,
                                                                                                                                              !1&)
      IL_0098:  brtrue.s   IL_00af

      IL_009a:  ldarg.1
      IL_009b:  ldloca.s   V_3
      IL_009d:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Key()
      IL_00a2:  call       class LoadedAssetBundle AssetBundleManager::LoadAssetBundle(string,
                                                                                       string)
      IL_00a7:  stloc.s    V_4
      IL_00a9:  ldloc.s    V_4
      IL_00ab:  brtrue.s   IL_00af

      IL_00ad:  leave.s    IL_012e

      IL_00af:  ldarg.3
      IL_00b0:  ldloca.s   V_3
      IL_00b2:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Key()
      IL_00b7:  stind.ref
      IL_00b8:  ldloc.s    V_4
      IL_00ba:  callvirt   instance class [UnityEngine.AssetBundleModule]UnityEngine.AssetBundle LoadedAssetBundle::get_Bundle()
      IL_00bf:  callvirt   instance string[] [UnityEngine.AssetBundleModule]UnityEngine.AssetBundle::GetAllAssetNames()
      IL_00c4:  ldsfld     class [mscorlib]System.Func`2<string,string> Studio.Info/'<>c'::'<>9__67_1'
      IL_00c9:  dup
      IL_00ca:  brtrue.s   IL_00e3

      IL_00cc:  pop
      IL_00cd:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
      IL_00d2:  ldftn      instance string Studio.Info/'<>c'::'<FindAllAssetName>b__67_1'(string)
      IL_00d8:  newobj     instance void class [mscorlib]System.Func`2<string,string>::.ctor(object,
                                                                                             native int)
      IL_00dd:  dup
      IL_00de:  stsfld     class [mscorlib]System.Func`2<string,string> Studio.Info/'<>c'::'<>9__67_1'
      IL_00e3:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<string,string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                    class [mscorlib]System.Func`2<!!0,!!1>)
      IL_00e8:  ldloc.0
      IL_00e9:  ldfld      class [mscorlib]System.Func`2<string,bool> Studio.Info/'<>c__DisplayClass67_0'::'<>9__2'
      IL_00ee:  dup
      IL_00ef:  brtrue.s   IL_0109

      IL_00f1:  pop
      IL_00f2:  ldloc.0
      IL_00f3:  ldloc.0
      IL_00f4:  ldftn      instance bool Studio.Info/'<>c__DisplayClass67_0'::'<FindAllAssetName>b__2'(string)
      IL_00fa:  newobj     instance void class [mscorlib]System.Func`2<string,bool>::.ctor(object,
                                                                                           native int)
      IL_00ff:  dup
      IL_0100:  stloc.s    V_5
      IL_0102:  stfld      class [mscorlib]System.Func`2<string,bool> Studio.Info/'<>c__DisplayClass67_0'::'<>9__2'
      IL_0107:  ldloc.s    V_5
      IL_0109:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Where<string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                            class [mscorlib]System.Func`2<!!0,bool>)
      IL_010e:  call       !!0[] [System.Core]System.Linq.Enumerable::ToArray<string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>)
      IL_0113:  stloc.s    V_6
      IL_0115:  leave.s    IL_0137

      IL_0117:  ldloc.2
      IL_0118:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_011d:  brtrue     IL_005e

      IL_0122:  leave.s    IL_012e

    }  // end .try
    finally
    {
      IL_0124:  ldloc.2
      IL_0125:  brfalse.s  IL_012d

      IL_0127:  ldloc.2
      IL_0128:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_012d:  endfinally
    }  // end handler
    IL_012e:  ldarg.3
    IL_012f:  ldstr      ""
    IL_0134:  stind.ref
    IL_0135:  ldloc.1
    IL_0136:  ret

    IL_0137:  ldloc.s    V_6
    IL_0139:  ret
  } // end of method Info::FindAllAssetName

  .method private hidebysig instance string[] 
          FindAllAssetNameFromBundle(string _bundlePath,
                                     string _regex,
                                     [out] string& _manifest) cil managed
  {
    // 代码大小       287 (0x11f)
    .maxstack  4
    .locals init (class Studio.Info/'<>c__DisplayClass68_0' V_0,
             class [mscorlib]System.Collections.Generic.IEnumerator`1<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>> V_1,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack> V_2,
             class LoadedAssetBundle V_3,
             class [mscorlib]System.Func`2<string,bool> V_4,
             string[] V_5)
    IL_0000:  newobj     instance void Studio.Info/'<>c__DisplayClass68_0'::.ctor()
    IL_0005:  stloc.0
    IL_0006:  ldloc.0
    IL_0007:  ldarg.1
    IL_0008:  stfld      string Studio.Info/'<>c__DisplayClass68_0'::_bundlePath
    IL_000d:  ldloc.0
    IL_000e:  ldarg.2
    IL_000f:  stfld      string Studio.Info/'<>c__DisplayClass68_0'::_regex
    IL_0014:  call       class [mscorlib]System.Collections.Generic.Dictionary`2<string,class AssetBundleManager/BundlePack> AssetBundleManager::get_ManifestBundlePack()
    IL_0019:  ldsfld     class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool> Studio.Info/'<>c'::'<>9__68_0'
    IL_001e:  dup
    IL_001f:  brtrue.s   IL_0038

    IL_0021:  pop
    IL_0022:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0027:  ldftn      instance bool Studio.Info/'<>c'::'<FindAllAssetNameFromBundle>b__68_0'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>)
    IL_002d:  newobj     instance void class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool>::.ctor(object,
                                                                                                                                                                                            native int)
    IL_0032:  dup
    IL_0033:  stsfld     class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool> Studio.Info/'<>c'::'<>9__68_0'
    IL_0038:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Where<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                                             class [mscorlib]System.Func`2<!!0,bool>)
    IL_003d:  ldloc.0
    IL_003e:  ldftn      instance bool Studio.Info/'<>c__DisplayClass68_0'::'<FindAllAssetNameFromBundle>b__1'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>)
    IL_0044:  newobj     instance void class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool>::.ctor(object,
                                                                                                                                                                                            native int)
    IL_0049:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Where<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                                             class [mscorlib]System.Func`2<!!0,bool>)
    IL_004e:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>::GetEnumerator()
    IL_0053:  stloc.1
    .try
    {
      IL_0054:  br         IL_00fc

      IL_0059:  ldloc.1
      IL_005a:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>::get_Current()
      IL_005f:  stloc.2
      IL_0060:  ldnull
      IL_0061:  stloc.3
      IL_0062:  ldloca.s   V_2
      IL_0064:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Value()
      IL_0069:  callvirt   instance class [mscorlib]System.Collections.Generic.Dictionary`2<string,class LoadedAssetBundle> AssetBundleManager/BundlePack::get_LoadedAssetBundles()
      IL_006e:  ldloc.0
      IL_006f:  ldfld      string Studio.Info/'<>c__DisplayClass68_0'::_bundlePath
      IL_0074:  ldloca.s   V_3
      IL_0076:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<string,class LoadedAssetBundle>::TryGetValue(!0,
                                                                                                                                              !1&)
      IL_007b:  brtrue.s   IL_0095

      IL_007d:  ldloc.0
      IL_007e:  ldfld      string Studio.Info/'<>c__DisplayClass68_0'::_bundlePath
      IL_0083:  ldloca.s   V_2
      IL_0085:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Key()
      IL_008a:  call       class LoadedAssetBundle AssetBundleManager::LoadAssetBundle(string,
                                                                                       string)
      IL_008f:  stloc.3
      IL_0090:  ldloc.3
      IL_0091:  brtrue.s   IL_0095

      IL_0093:  leave.s    IL_0113

      IL_0095:  ldarg.3
      IL_0096:  ldloca.s   V_2
      IL_0098:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Key()
      IL_009d:  stind.ref
      IL_009e:  ldloc.3
      IL_009f:  callvirt   instance class [UnityEngine.AssetBundleModule]UnityEngine.AssetBundle LoadedAssetBundle::get_Bundle()
      IL_00a4:  callvirt   instance string[] [UnityEngine.AssetBundleModule]UnityEngine.AssetBundle::GetAllAssetNames()
      IL_00a9:  ldsfld     class [mscorlib]System.Func`2<string,string> Studio.Info/'<>c'::'<>9__68_2'
      IL_00ae:  dup
      IL_00af:  brtrue.s   IL_00c8

      IL_00b1:  pop
      IL_00b2:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
      IL_00b7:  ldftn      instance string Studio.Info/'<>c'::'<FindAllAssetNameFromBundle>b__68_2'(string)
      IL_00bd:  newobj     instance void class [mscorlib]System.Func`2<string,string>::.ctor(object,
                                                                                             native int)
      IL_00c2:  dup
      IL_00c3:  stsfld     class [mscorlib]System.Func`2<string,string> Studio.Info/'<>c'::'<>9__68_2'
      IL_00c8:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<string,string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                    class [mscorlib]System.Func`2<!!0,!!1>)
      IL_00cd:  ldloc.0
      IL_00ce:  ldfld      class [mscorlib]System.Func`2<string,bool> Studio.Info/'<>c__DisplayClass68_0'::'<>9__3'
      IL_00d3:  dup
      IL_00d4:  brtrue.s   IL_00ee

      IL_00d6:  pop
      IL_00d7:  ldloc.0
      IL_00d8:  ldloc.0
      IL_00d9:  ldftn      instance bool Studio.Info/'<>c__DisplayClass68_0'::'<FindAllAssetNameFromBundle>b__3'(string)
      IL_00df:  newobj     instance void class [mscorlib]System.Func`2<string,bool>::.ctor(object,
                                                                                           native int)
      IL_00e4:  dup
      IL_00e5:  stloc.s    V_4
      IL_00e7:  stfld      class [mscorlib]System.Func`2<string,bool> Studio.Info/'<>c__DisplayClass68_0'::'<>9__3'
      IL_00ec:  ldloc.s    V_4
      IL_00ee:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Where<string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                            class [mscorlib]System.Func`2<!!0,bool>)
      IL_00f3:  call       !!0[] [System.Core]System.Linq.Enumerable::ToArray<string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>)
      IL_00f8:  stloc.s    V_5
      IL_00fa:  leave.s    IL_011c

      IL_00fc:  ldloc.1
      IL_00fd:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_0102:  brtrue     IL_0059

      IL_0107:  leave.s    IL_0113

    }  // end .try
    finally
    {
      IL_0109:  ldloc.1
      IL_010a:  brfalse.s  IL_0112

      IL_010c:  ldloc.1
      IL_010d:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0112:  endfinally
    }  // end handler
    IL_0113:  ldarg.3
    IL_0114:  ldstr      ""
    IL_0119:  stind.ref
    IL_011a:  ldnull
    IL_011b:  ret

    IL_011c:  ldloc.s    V_5
    IL_011e:  ret
  } // end of method Info::FindAllAssetNameFromBundle

  .method private hidebysig instance void 
          LoadAccessoryGroupInfo(class [IL]ExcelData _ed) cil managed
  {
    // 代码大小       279 (0x117)
    .maxstack  5
    .locals init (int32 V_0,
             class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_1,
             class [mscorlib]System.Collections.Generic.List`1<string> V_2,
             int32 V_3,
             string V_4,
             valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.Info/AccessoryGroupInfo> V_5,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/AccessoryGroupInfo> V_6,
             int32 V_7,
             int32 V_8)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.1
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__69_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadAccessoryGroupInfo>b__69_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__69_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.1
    .try
    {
      IL_0040:  br.s       IL_0087

      IL_0042:  ldloc.1
      IL_0043:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_0048:  stloc.2
      IL_0049:  ldc.i4.m1
      IL_004a:  stloc.3
      IL_004b:  ldloc.2
      IL_004c:  ldc.i4.0
      IL_004d:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0052:  ldloca.s   V_3
      IL_0054:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0059:  brfalse.s  IL_0087

      IL_005b:  ldloc.2
      IL_005c:  ldc.i4.1
      IL_005d:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0062:  stloc.s    V_4
      IL_0064:  ldloc.s    V_4
      IL_0066:  call       bool [IL]NullCheck::IsNullOrEmpty(string)
      IL_006b:  brtrue.s   IL_0087

      IL_006d:  ldarg.0
      IL_006e:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AccessoryGroupInfo> Studio.Info::dicAccessoryGroup
      IL_0073:  ldloc.3
      IL_0074:  ldloc.s    V_4
      IL_0076:  ldloc.2
      IL_0077:  ldc.i4.2
      IL_0078:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_007d:  newobj     instance void Studio.Info/AccessoryGroupInfo::.ctor(string,
                                                                               string)
      IL_0082:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AccessoryGroupInfo>::set_Item(!0,
                                                                                                                                                       !1)
      IL_0087:  ldloc.1
      IL_0088:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_008d:  brtrue.s   IL_0042

      IL_008f:  leave.s    IL_009b

    }  // end .try
    finally
    {
      IL_0091:  ldloc.1
      IL_0092:  brfalse.s  IL_009a

      IL_0094:  ldloc.1
      IL_0095:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_009a:  endfinally
    }  // end handler
    IL_009b:  ldarg.0
    IL_009c:  ldarg.1
    IL_009d:  stfld      class [IL]ExcelData Studio.Info::m_AccessoryPointGroup
    IL_00a2:  ldc.i4.0
    IL_00a3:  stloc.0
    IL_00a4:  ldarg.0
    IL_00a5:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AccessoryGroupInfo> Studio.Info::dicAccessoryGroup
    IL_00aa:  callvirt   instance valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<!0,!1> class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AccessoryGroupInfo>::GetEnumerator()
    IL_00af:  stloc.s    V_5
    .try
    {
      IL_00b1:  br.s       IL_00f6

      IL_00b3:  ldloca.s   V_5
      IL_00b5:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.Info/AccessoryGroupInfo>::get_Current()
      IL_00ba:  stloc.s    V_6
      IL_00bc:  ldloca.s   V_6
      IL_00be:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/AccessoryGroupInfo>::get_Value()
      IL_00c3:  callvirt   instance int32[] Studio.Info/AccessoryGroupInfo::get_Targets()
      IL_00c8:  ldc.i4.0
      IL_00c9:  call       !!0 [IL]NullCheck::SafeGet<int32>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                             int32)
      IL_00ce:  ldloca.s   V_6
      IL_00d0:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/AccessoryGroupInfo>::get_Value()
      IL_00d5:  callvirt   instance int32[] Studio.Info/AccessoryGroupInfo::get_Targets()
      IL_00da:  ldc.i4.1
      IL_00db:  call       !!0 [IL]NullCheck::SafeGet<int32>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                             int32)
      IL_00e0:  stloc.s    V_7
      IL_00e2:  stloc.s    V_8
      IL_00e4:  br.s       IL_00f0

      IL_00e6:  ldloc.0
      IL_00e7:  ldc.i4.1
      IL_00e8:  add
      IL_00e9:  stloc.0
      IL_00ea:  ldloc.s    V_8
      IL_00ec:  ldc.i4.1
      IL_00ed:  add
      IL_00ee:  stloc.s    V_8
      IL_00f0:  ldloc.s    V_8
      IL_00f2:  ldloc.s    V_7
      IL_00f4:  ble.s      IL_00e6

      IL_00f6:  ldloca.s   V_5
      IL_00f8:  call       instance bool valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.Info/AccessoryGroupInfo>::MoveNext()
      IL_00fd:  brtrue.s   IL_00b3

      IL_00ff:  leave.s    IL_010f

    }  // end .try
    finally
    {
      IL_0101:  ldloca.s   V_5
      IL_0103:  constrained. valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.Info/AccessoryGroupInfo>
      IL_0109:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_010e:  endfinally
    }  // end handler
    IL_010f:  ldarg.0
    IL_0110:  ldloc.0
    IL_0111:  call       instance void Studio.Info::set_AccessoryPointNum(int32)
    IL_0116:  ret
  } // end of method Info::LoadAccessoryGroupInfo

  .method private hidebysig instance void 
          LoadBoneInfo(class [IL]ExcelData _ed,
                       class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/BoneInfo> _dic) cil managed
  {
    // 代码大小       156 (0x9c)
    .maxstack  5
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             int32 V_3,
             string V_4)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.1
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__70_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadBoneInfo>b__70_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__70_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br.s       IL_0087

      IL_0042:  ldloc.0
      IL_0043:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_0048:  stloc.1
      IL_0049:  ldc.i4.0
      IL_004a:  stloc.2
      IL_004b:  ldc.i4.m1
      IL_004c:  stloc.3
      IL_004d:  ldloc.1
      IL_004e:  ldloc.2
      IL_004f:  dup
      IL_0050:  ldc.i4.1
      IL_0051:  add
      IL_0052:  stloc.2
      IL_0053:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0058:  ldloca.s   V_3
      IL_005a:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_005f:  brfalse.s  IL_0087

      IL_0061:  ldloc.1
      IL_0062:  ldloc.2
      IL_0063:  dup
      IL_0064:  ldc.i4.1
      IL_0065:  add
      IL_0066:  stloc.2
      IL_0067:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_006c:  stloc.s    V_4
      IL_006e:  ldloc.s    V_4
      IL_0070:  call       bool [IL]NullCheck::IsNullOrEmpty(string)
      IL_0075:  brtrue.s   IL_0087

      IL_0077:  ldarg.2
      IL_0078:  ldloc.3
      IL_0079:  ldloc.3
      IL_007a:  ldloc.s    V_4
      IL_007c:  ldloc.1
      IL_007d:  newobj     instance void Studio.Info/BoneInfo::.ctor(int32,
                                                                     string,
                                                                     class [mscorlib]System.Collections.Generic.List`1<string>)
      IL_0082:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/BoneInfo>::set_Item(!0,
                                                                                                                                             !1)
      IL_0087:  ldloc.0
      IL_0088:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_008d:  brtrue.s   IL_0042

      IL_008f:  leave.s    IL_009b

    }  // end .try
    finally
    {
      IL_0091:  ldloc.0
      IL_0092:  brfalse.s  IL_009a

      IL_0094:  ldloc.0
      IL_0095:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_009a:  endfinally
    }  // end handler
    IL_009b:  ret
  } // end of method Info::LoadBoneInfo

  .method private hidebysig instance class [mscorlib]System.Collections.IEnumerator 
          LoadItemLoadInfoCoroutine(string _bundlePath,
                                    string _regex) cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.IteratorStateMachineAttribute::.ctor(class [mscorlib]System.Type) = ( 01 00 2C 53 74 75 64 69 6F 2E 49 6E 66 6F 2B 3C   // ..,Studio.Info+<
                                                                                                                                          4C 6F 61 64 49 74 65 6D 4C 6F 61 64 49 6E 66 6F   // LoadItemLoadInfo
                                                                                                                                          43 6F 72 6F 75 74 69 6E 65 3E 64 5F 5F 37 31 00   // Coroutine>d__71.
                                                                                                                                          00 ) 
    // 代码大小       28 (0x1c)
    .maxstack  8
    IL_0000:  ldc.i4.0
    IL_0001:  newobj     instance void Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::.ctor(int32)
    IL_0006:  dup
    IL_0007:  ldarg.0
    IL_0008:  stfld      class Studio.Info Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::'<>4__this'
    IL_000d:  dup
    IL_000e:  ldarg.1
    IL_000f:  stfld      string Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::_bundlePath
    IL_0014:  dup
    IL_0015:  ldarg.2
    IL_0016:  stfld      string Studio.Info/'<LoadItemLoadInfoCoroutine>d__71'::_regex
    IL_001b:  ret
  } // end of method Info::LoadItemLoadInfoCoroutine

  .method private hidebysig instance void 
          SortDictionary(string[] files,
                         string _regex,
                         class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> _sortDic) cil managed
  {
    // 代码大小       172 (0xac)
    .maxstack  5
    .locals init (string V_0,
             int32 V_1,
             int32 V_2,
             int32 V_3)
    IL_0000:  ldarg.2
    IL_0001:  ldc.i4.1
    IL_0002:  newarr     [mscorlib]System.Char
    IL_0007:  dup
    IL_0008:  ldc.i4.0
    IL_0009:  ldc.i4.s   95
    IL_000b:  stelem.i2
    IL_000c:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
    IL_0011:  ldc.i4.0
    IL_0012:  ldelem.ref
    IL_0013:  callvirt   instance string [mscorlib]System.String::ToLower()
    IL_0018:  stloc.0
    IL_0019:  ldc.i4.0
    IL_001a:  stloc.1
    IL_001b:  br         IL_00a2

    IL_0020:  ldarg.1
    IL_0021:  ldloc.1
    IL_0022:  ldelem.ref
    IL_0023:  ldc.i4.1
    IL_0024:  newarr     [mscorlib]System.Char
    IL_0029:  dup
    IL_002a:  ldc.i4.0
    IL_002b:  ldc.i4.s   95
    IL_002d:  stelem.i2
    IL_002e:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
    IL_0033:  ldc.i4.0
    IL_0034:  ldelem.ref
    IL_0035:  callvirt   instance string [mscorlib]System.String::ToLower()
    IL_003a:  ldloc.0
    IL_003b:  callvirt   instance int32 [mscorlib]System.String::CompareTo(string)
    IL_0040:  brtrue.s   IL_009e

    IL_0042:  ldarg.1
    IL_0043:  ldloc.1
    IL_0044:  ldelem.ref
    IL_0045:  ldarg.2
    IL_0046:  ldc.i4.1
    IL_0047:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                string,
                                                                                                                                valuetype [System]System.Text.RegularExpressions.RegexOptions)
    IL_004c:  dup
    IL_004d:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
    IL_0052:  ldc.i4.1
    IL_0053:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
    IL_0058:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
    IL_005d:  call       int32 [mscorlib]System.Int32::Parse(string)
    IL_0062:  stloc.2
    IL_0063:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
    IL_0068:  ldc.i4.2
    IL_0069:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
    IL_006e:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
    IL_0073:  call       int32 [mscorlib]System.Int32::Parse(string)
    IL_0078:  stloc.3
    IL_0079:  ldarg.3
    IL_007a:  ldloc.2
    IL_007b:  callvirt   instance bool class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::ContainsKey(!0)
    IL_0080:  brtrue.s   IL_008e

    IL_0082:  ldarg.3
    IL_0083:  ldloc.2
    IL_0084:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::.ctor()
    IL_0089:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::Add(!0,
                                                                                                                                                                                         !1)
    IL_008e:  ldarg.3
    IL_008f:  ldloc.2
    IL_0090:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Item(!0)
    IL_0095:  ldloc.3
    IL_0096:  ldarg.1
    IL_0097:  ldloc.1
    IL_0098:  ldelem.ref
    IL_0099:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::Add(!0,
                                                                                                                      !1)
    IL_009e:  ldloc.1
    IL_009f:  ldc.i4.1
    IL_00a0:  add
    IL_00a1:  stloc.1
    IL_00a2:  ldloc.1
    IL_00a3:  ldarg.1
    IL_00a4:  ldlen
    IL_00a5:  conv.i4
    IL_00a6:  blt        IL_0020

    IL_00ab:  ret
  } // end of method Info::SortDictionary

  .method private hidebysig instance void 
          LoadItemLoadInfo(class [IL]ExcelData _ed) cil managed
  {
    // 代码大小       257 (0x101)
    .maxstack  3
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             int32 V_3,
             int32 V_4)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.1
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__73_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadItemLoadInfo>b__73_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__73_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br         IL_00e9

      IL_0045:  ldloc.0
      IL_0046:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_004b:  stloc.1
      IL_004c:  ldc.i4.m1
      IL_004d:  stloc.2
      IL_004e:  ldloc.1
      IL_004f:  ldc.i4.0
      IL_0050:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0055:  ldloca.s   V_2
      IL_0057:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_005c:  brtrue.s   IL_0063

      IL_005e:  leave      IL_0100

      IL_0063:  ldloc.1
      IL_0064:  ldc.i4.1
      IL_0065:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_006a:  call       int32 [mscorlib]System.Int32::Parse(string)
      IL_006f:  stloc.3
      IL_0070:  ldloc.1
      IL_0071:  ldc.i4.2
      IL_0072:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0077:  call       int32 [mscorlib]System.Int32::Parse(string)
      IL_007c:  stloc.s    V_4
      IL_007e:  ldarg.0
      IL_007f:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>> Studio.Info::dicItemLoadInfo
      IL_0084:  ldloc.3
      IL_0085:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>>::ContainsKey(!0)
      IL_008a:  brtrue.s   IL_009d

      IL_008c:  ldarg.0
      IL_008d:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>> Studio.Info::dicItemLoadInfo
      IL_0092:  ldloc.3
      IL_0093:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>::.ctor()
      IL_0098:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>>::set_Item(!0,
                                                                                                                                                                                                                                                                               !1)
      IL_009d:  ldarg.0
      IL_009e:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>> Studio.Info::dicItemLoadInfo
      IL_00a3:  ldloc.3
      IL_00a4:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>>::get_Item(!0)
      IL_00a9:  ldloc.s    V_4
      IL_00ab:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>::ContainsKey(!0)
      IL_00b0:  brtrue.s   IL_00ca

      IL_00b2:  ldarg.0
      IL_00b3:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>> Studio.Info::dicItemLoadInfo
      IL_00b8:  ldloc.3
      IL_00b9:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>>::get_Item(!0)
      IL_00be:  ldloc.s    V_4
      IL_00c0:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>::.ctor()
      IL_00c5:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>::set_Item(!0,
                                                                                                                                                                                                                !1)
      IL_00ca:  ldarg.0
      IL_00cb:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>> Studio.Info::dicItemLoadInfo
      IL_00d0:  ldloc.3
      IL_00d1:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>>::get_Item(!0)
      IL_00d6:  ldloc.s    V_4
      IL_00d8:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>::get_Item(!0)
      IL_00dd:  ldloc.2
      IL_00de:  ldloc.1
      IL_00df:  newobj     instance void Studio.Info/ItemLoadInfo::.ctor(class [mscorlib]System.Collections.Generic.List`1<string>)
      IL_00e4:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>::set_Item(!0,
                                                                                                                                                 !1)
      IL_00e9:  ldloc.0
      IL_00ea:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00ef:  brtrue     IL_0045

      IL_00f4:  leave.s    IL_0100

    }  // end .try
    finally
    {
      IL_00f6:  ldloc.0
      IL_00f7:  brfalse.s  IL_00ff

      IL_00f9:  ldloc.0
      IL_00fa:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00ff:  endfinally
    }  // end handler
    IL_0100:  ret
  } // end of method Info::LoadItemLoadInfo

  .method private hidebysig instance void 
          LoadItemBoneInfo(string _bundlePath,
                           string _regex) cil managed
  {
    // 代码大小       170 (0xaa)
    .maxstack  5
    .locals init (string V_0,
             string[] V_1,
             class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_2,
             valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_3,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_4,
             valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> V_5,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string> V_6)
    IL_0000:  ldstr      ""
    IL_0005:  stloc.0
    IL_0006:  ldarg.0
    IL_0007:  ldarg.1
    IL_0008:  ldarg.2
    IL_0009:  ldloca.s   V_0
    IL_000b:  call       instance string[] Studio.Info::FindAllAssetName(string,
                                                                         string,
                                                                         string&)
    IL_0010:  stloc.1
    IL_0011:  ldloc.1
    IL_0012:  call       bool [IL]NullCheck::IsNullOrEmpty<string>(class [mscorlib]System.Collections.Generic.IReadOnlyCollection`1<!!0>)
    IL_0017:  brfalse.s  IL_001a

    IL_0019:  ret

    IL_001a:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::.ctor()
    IL_001f:  stloc.2
    IL_0020:  ldarg.0
    IL_0021:  ldloc.1
    IL_0022:  ldarg.2
    IL_0023:  ldloc.2
    IL_0024:  call       instance void Studio.Info::SortDictionary(string[],
                                                                   string,
                                                                   class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>)
    IL_0029:  ldloc.2
    IL_002a:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::GetEnumerator()
    IL_002f:  stloc.3
    .try
    {
      IL_0030:  br.s       IL_0090

      IL_0032:  ldloca.s   V_3
      IL_0034:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Current()
      IL_0039:  stloc.s    V_4
      IL_003b:  ldloca.s   V_4
      IL_003d:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Value()
      IL_0042:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::GetEnumerator()
      IL_0047:  stloc.s    V_5
      .try
      {
        IL_0049:  br.s       IL_0077

        IL_004b:  ldloca.s   V_5
        IL_004d:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::get_Current()
        IL_0052:  stloc.s    V_6
        IL_0054:  ldarg.0
        IL_0055:  ldarg.0
        IL_0056:  ldarg.1
        IL_0057:  ldloca.s   V_6
        IL_0059:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string>::get_Value()
        IL_005e:  ldloc.0
        IL_005f:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                     string,
                                                                                     string)
        IL_0064:  ldloca.s   V_4
        IL_0066:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Key()
        IL_006b:  ldloca.s   V_6
        IL_006d:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string>::get_Key()
        IL_0072:  call       instance void Studio.Info::LoadItemBoneInfo(class [IL]ExcelData,
                                                                         int32,
                                                                         int32)
        IL_0077:  ldloca.s   V_5
        IL_0079:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::MoveNext()
        IL_007e:  brtrue.s   IL_004b

        IL_0080:  leave.s    IL_0090

      }  // end .try
      finally
      {
        IL_0082:  ldloca.s   V_5
        IL_0084:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>
        IL_008a:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
        IL_008f:  endfinally
      }  // end handler
      IL_0090:  ldloca.s   V_3
      IL_0092:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::MoveNext()
      IL_0097:  brtrue.s   IL_0032

      IL_0099:  leave.s    IL_00a9

    }  // end .try
    finally
    {
      IL_009b:  ldloca.s   V_3
      IL_009d:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>
      IL_00a3:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00a8:  endfinally
    }  // end handler
    IL_00a9:  ret
  } // end of method Info::LoadItemBoneInfo

  .method private hidebysig instance void 
          LoadItemColorData(string _bundlePath,
                            string _file) cil managed
  {
    // 代码大小       524 (0x20c)
    .maxstack  5
    .locals init (class Studio.Info/'<>c__DisplayClass75_0' V_0,
             string V_1,
             class Studio.ItemColorData V_2,
             bool V_3,
             class [mscorlib]System.Collections.Generic.IEnumerator`1<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>> V_4,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack> V_5,
             class [mscorlib]System.Predicate`1<string> V_6,
             valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>> V_7,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>> V_8,
             class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>> V_9,
             valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>> V_10,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>> V_11,
             class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData> V_12,
             valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.ItemColorData/ColorData> V_13,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.ItemColorData/ColorData> V_14)
    IL_0000:  newobj     instance void Studio.Info/'<>c__DisplayClass75_0'::.ctor()
    IL_0005:  stloc.0
    IL_0006:  ldloc.0
    IL_0007:  ldarg.1
    IL_0008:  stfld      string Studio.Info/'<>c__DisplayClass75_0'::_bundlePath
    IL_000d:  ldstr      ""
    IL_0012:  stloc.1
    IL_0013:  call       bool Studio.AssetBundleCheck::get_IsSimulation()
    IL_0018:  brfalse.s  IL_002d

    IL_001a:  ldloc.0
    IL_001b:  ldfld      string Studio.Info/'<>c__DisplayClass75_0'::_bundlePath
    IL_0020:  ldarg.2
    IL_0021:  ldc.i4.0
    IL_0022:  call       bool Studio.AssetBundleCheck::FindFile(string,
                                                                string,
                                                                bool)
    IL_0027:  brtrue     IL_00d7

    IL_002c:  ret

    IL_002d:  ldc.i4.0
    IL_002e:  stloc.3
    IL_002f:  call       class [mscorlib]System.Collections.Generic.Dictionary`2<string,class AssetBundleManager/BundlePack> AssetBundleManager::get_ManifestBundlePack()
    IL_0034:  ldsfld     class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool> Studio.Info/'<>c'::'<>9__75_0'
    IL_0039:  dup
    IL_003a:  brtrue.s   IL_0053

    IL_003c:  pop
    IL_003d:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0042:  ldftn      instance bool Studio.Info/'<>c'::'<LoadItemColorData>b__75_0'(valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>)
    IL_0048:  newobj     instance void class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool>::.ctor(object,
                                                                                                                                                                                            native int)
    IL_004d:  dup
    IL_004e:  stsfld     class [mscorlib]System.Func`2<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>,bool> Studio.Info/'<>c'::'<>9__75_0'
    IL_0053:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Where<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                                             class [mscorlib]System.Func`2<!!0,bool>)
    IL_0058:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>::GetEnumerator()
    IL_005d:  stloc.s    V_4
    .try
    {
      IL_005f:  br.s       IL_00bc

      IL_0061:  ldloc.s    V_4
      IL_0063:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>>::get_Current()
      IL_0068:  stloc.s    V_5
      IL_006a:  ldloc.3
      IL_006b:  ldloca.s   V_5
      IL_006d:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Value()
      IL_0072:  callvirt   instance class [UnityEngine.AssetBundleModule]UnityEngine.AssetBundleManifest AssetBundleManager/BundlePack::get_AssetBundleManifest()
      IL_0077:  callvirt   instance string[] [UnityEngine.AssetBundleModule]UnityEngine.AssetBundleManifest::GetAllAssetBundles()
      IL_007c:  call       class [mscorlib]System.Collections.Generic.List`1<!!0> [System.Core]System.Linq.Enumerable::ToList<string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>)
      IL_0081:  ldloc.0
      IL_0082:  ldfld      class [mscorlib]System.Predicate`1<string> Studio.Info/'<>c__DisplayClass75_0'::'<>9__1'
      IL_0087:  dup
      IL_0088:  brtrue.s   IL_00a2

      IL_008a:  pop
      IL_008b:  ldloc.0
      IL_008c:  ldloc.0
      IL_008d:  ldftn      instance bool Studio.Info/'<>c__DisplayClass75_0'::'<LoadItemColorData>b__1'(string)
      IL_0093:  newobj     instance void class [mscorlib]System.Predicate`1<string>::.ctor(object,
                                                                                           native int)
      IL_0098:  dup
      IL_0099:  stloc.s    V_6
      IL_009b:  stfld      class [mscorlib]System.Predicate`1<string> Studio.Info/'<>c__DisplayClass75_0'::'<>9__1'
      IL_00a0:  ldloc.s    V_6
      IL_00a2:  callvirt   instance int32 class [mscorlib]System.Collections.Generic.List`1<string>::FindIndex(class [mscorlib]System.Predicate`1<!0>)
      IL_00a7:  ldc.i4.m1
      IL_00a8:  ceq
      IL_00aa:  ldc.i4.0
      IL_00ab:  ceq
      IL_00ad:  or
      IL_00ae:  stloc.3
      IL_00af:  ldloc.3
      IL_00b0:  brfalse.s  IL_00bc

      IL_00b2:  ldloca.s   V_5
      IL_00b4:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string,class AssetBundleManager/BundlePack>::get_Key()
      IL_00b9:  stloc.1
      IL_00ba:  leave.s    IL_00d3

      IL_00bc:  ldloc.s    V_4
      IL_00be:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00c3:  brtrue.s   IL_0061

      IL_00c5:  leave.s    IL_00d3

    }  // end .try
    finally
    {
      IL_00c7:  ldloc.s    V_4
      IL_00c9:  brfalse.s  IL_00d2

      IL_00cb:  ldloc.s    V_4
      IL_00cd:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00d2:  endfinally
    }  // end handler
    IL_00d3:  ldloc.3
    IL_00d4:  brtrue.s   IL_00d7

    IL_00d6:  ret

    IL_00d7:  ldloc.0
    IL_00d8:  ldfld      string Studio.Info/'<>c__DisplayClass75_0'::_bundlePath
    IL_00dd:  ldarg.2
    IL_00de:  ldc.i4.0
    IL_00df:  ldloc.1
    IL_00e0:  call       !!0 CommonLib::LoadAsset<class Studio.ItemColorData>(string,
                                                                              string,
                                                                              bool,
                                                                              string)
    IL_00e5:  stloc.2
    IL_00e6:  ldloc.2
    IL_00e7:  ldnull
    IL_00e8:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_00ed:  brfalse.s  IL_00f0

    IL_00ef:  ret

    IL_00f0:  ldloc.2
    IL_00f1:  callvirt   instance class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>> Studio.ItemColorData::get_ColorDatas()
    IL_00f6:  callvirt   instance valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<!0,!1> class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>>::GetEnumerator()
    IL_00fb:  stloc.s    V_7
    .try
    {
      IL_00fd:  br         IL_01ef

      IL_0102:  ldloca.s   V_7
      IL_0104:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>>::get_Current()
      IL_0109:  stloc.s    V_8
      IL_010b:  ldnull
      IL_010c:  stloc.s    V_9
      IL_010e:  ldarg.0
      IL_010f:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>> Studio.Info::dicItemColorData
      IL_0114:  ldloca.s   V_8
      IL_0116:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>>::get_Key()
      IL_011b:  ldloca.s   V_9
      IL_011d:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>>::TryGetValue(!0,
                                                                                                                                                                                                                                                                                        !1&)
      IL_0122:  brtrue.s   IL_013f

      IL_0124:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>::.ctor()
      IL_0129:  stloc.s    V_9
      IL_012b:  ldarg.0
      IL_012c:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>> Studio.Info::dicItemColorData
      IL_0131:  ldloca.s   V_8
      IL_0133:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>>::get_Key()
      IL_0138:  ldloc.s    V_9
      IL_013a:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>>::Add(!0,
                                                                                                                                                                                                                                                                                !1)
      IL_013f:  ldloca.s   V_8
      IL_0141:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>>::get_Value()
      IL_0146:  callvirt   instance valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<!0,!1> class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>::GetEnumerator()
      IL_014b:  stloc.s    V_10
      .try
      {
        IL_014d:  br         IL_01d3

        IL_0152:  ldloca.s   V_10
        IL_0154:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>::get_Current()
        IL_0159:  stloc.s    V_11
        IL_015b:  ldnull
        IL_015c:  stloc.s    V_12
        IL_015e:  ldloc.s    V_9
        IL_0160:  ldloca.s   V_11
        IL_0162:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>::get_Key()
        IL_0167:  ldloca.s   V_12
        IL_0169:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>::TryGetValue(!0,
                                                                                                                                                                                                                           !1&)
        IL_016e:  brtrue.s   IL_0187

        IL_0170:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>::.ctor()
        IL_0175:  stloc.s    V_12
        IL_0177:  ldloc.s    V_9
        IL_0179:  ldloca.s   V_11
        IL_017b:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>::get_Key()
        IL_0180:  ldloc.s    V_12
        IL_0182:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>::Add(!0,
                                                                                                                                                                                                                   !1)
        IL_0187:  ldloca.s   V_11
        IL_0189:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>::get_Value()
        IL_018e:  callvirt   instance valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<!0,!1> class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>::GetEnumerator()
        IL_0193:  stloc.s    V_13
        .try
        {
          IL_0195:  br.s       IL_01ba

          IL_0197:  ldloca.s   V_13
          IL_0199:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.ItemColorData/ColorData>::get_Current()
          IL_019e:  stloc.s    V_14
          IL_01a0:  ldloc.s    V_12
          IL_01a2:  ldloca.s   V_14
          IL_01a4:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.ItemColorData/ColorData>::get_Key()
          IL_01a9:  ldloca.s   V_14
          IL_01ab:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.ItemColorData/ColorData>::get_Value()
          IL_01b0:  newobj     instance void Studio.ItemColorData/ColorData::.ctor(class Studio.ItemColorData/ColorData)
          IL_01b5:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>::set_Item(!0,
                                                                                                                                                           !1)
          IL_01ba:  ldloca.s   V_13
          IL_01bc:  call       instance bool valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.ItemColorData/ColorData>::MoveNext()
          IL_01c1:  brtrue.s   IL_0197

          IL_01c3:  leave.s    IL_01d3

        }  // end .try
        finally
        {
          IL_01c5:  ldloca.s   V_13
          IL_01c7:  constrained. valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.ItemColorData/ColorData>
          IL_01cd:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
          IL_01d2:  endfinally
        }  // end handler
        IL_01d3:  ldloca.s   V_10
        IL_01d5:  call       instance bool valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>::MoveNext()
        IL_01da:  brtrue     IL_0152

        IL_01df:  leave.s    IL_01ef

      }  // end .try
      finally
      {
        IL_01e1:  ldloca.s   V_10
        IL_01e3:  constrained. valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>
        IL_01e9:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
        IL_01ee:  endfinally
      }  // end handler
      IL_01ef:  ldloca.s   V_7
      IL_01f1:  call       instance bool valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>>::MoveNext()
      IL_01f6:  brtrue     IL_0102

      IL_01fb:  leave.s    IL_020b

    }  // end .try
    finally
    {
      IL_01fd:  ldloca.s   V_7
      IL_01ff:  constrained. valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>>
      IL_0205:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_020a:  endfinally
    }  // end handler
    IL_020b:  ret
  } // end of method Info::LoadItemColorData

  .method private hidebysig instance void 
          LoadItemBoneInfo(class [IL]ExcelData _ed,
                           int32 _group,
                           int32 _category) cil managed
  {
    // 代码大小       216 (0xd8)
    .maxstack  4
    .locals init (class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>> V_0,
             class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo> V_1,
             class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_2,
             class [mscorlib]System.Collections.Generic.List`1<string> V_3,
             class Studio.Info/ItemLoadInfo V_4,
             int32 V_5)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldnull
    IL_000b:  stloc.0
    IL_000c:  ldarg.0
    IL_000d:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>> Studio.Info::dicItemLoadInfo
    IL_0012:  ldarg.2
    IL_0013:  ldloca.s   V_0
    IL_0015:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>>::TryGetValue(!0,
                                                                                                                                                                                                                                                                                !1&)
    IL_001a:  brtrue.s   IL_001d

    IL_001c:  ret

    IL_001d:  ldnull
    IL_001e:  stloc.1
    IL_001f:  ldloc.0
    IL_0020:  ldarg.3
    IL_0021:  ldloca.s   V_1
    IL_0023:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>::TryGetValue(!0,
                                                                                                                                                                                                                 !1&)
    IL_0028:  brtrue.s   IL_002b

    IL_002a:  ret

    IL_002b:  ldarg.1
    IL_002c:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0031:  ldc.i4.1
    IL_0032:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0037:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__76_0'
    IL_003c:  dup
    IL_003d:  brtrue.s   IL_0056

    IL_003f:  pop
    IL_0040:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0045:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadItemBoneInfo>b__76_0'(class [IL]ExcelData/Param)
    IL_004b:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_0050:  dup
    IL_0051:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__76_0'
    IL_0056:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_005b:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_0060:  stloc.2
    .try
    {
      IL_0061:  br.s       IL_00c3

      IL_0063:  ldloc.2
      IL_0064:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_0069:  stloc.3
      IL_006a:  ldnull
      IL_006b:  stloc.s    V_4
      IL_006d:  ldc.i4.m1
      IL_006e:  stloc.s    V_5
      IL_0070:  ldloc.3
      IL_0071:  ldc.i4.0
      IL_0072:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0077:  ldloca.s   V_5
      IL_0079:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_007e:  brfalse.s  IL_00c3

      IL_0080:  ldloc.1
      IL_0081:  ldloc.s    V_5
      IL_0083:  ldloca.s   V_4
      IL_0085:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>::TryGetValue(!0,
                                                                                                                                                    !1&)
      IL_008a:  brfalse.s  IL_00c3

      IL_008c:  ldloc.s    V_4
      IL_008e:  ldloc.3
      IL_008f:  ldc.i4.1
      IL_0090:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                           int32)
      IL_0095:  ldsfld     class [mscorlib]System.Func`2<string,bool> Studio.Info/'<>c'::'<>9__76_1'
      IL_009a:  dup
      IL_009b:  brtrue.s   IL_00b4

      IL_009d:  pop
      IL_009e:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
      IL_00a3:  ldftn      instance bool Studio.Info/'<>c'::'<LoadItemBoneInfo>b__76_1'(string)
      IL_00a9:  newobj     instance void class [mscorlib]System.Func`2<string,bool>::.ctor(object,
                                                                                           native int)
      IL_00ae:  dup
      IL_00af:  stsfld     class [mscorlib]System.Func`2<string,bool> Studio.Info/'<>c'::'<>9__76_1'
      IL_00b4:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Where<string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                            class [mscorlib]System.Func`2<!!0,bool>)
      IL_00b9:  call       class [mscorlib]System.Collections.Generic.List`1<!!0> [System.Core]System.Linq.Enumerable::ToList<string>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>)
      IL_00be:  stfld      class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/ItemLoadInfo::bones
      IL_00c3:  ldloc.2
      IL_00c4:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00c9:  brtrue.s   IL_0063

      IL_00cb:  leave.s    IL_00d7

    }  // end .try
    finally
    {
      IL_00cd:  ldloc.2
      IL_00ce:  brfalse.s  IL_00d6

      IL_00d0:  ldloc.2
      IL_00d1:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00d6:  endfinally
    }  // end handler
    IL_00d7:  ret
  } // end of method Info::LoadItemBoneInfo

  .method private hidebysig instance void 
          LoadLightLoadInfo(class [IL]ExcelData _ed) cil managed
  {
    // 代码大小       238 (0xee)
    .maxstack  5
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             class Studio.Info/LightLoadInfo V_3)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.1
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__77_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadLightLoadInfo>b__77_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__77_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br         IL_00d6

      IL_0045:  ldloc.0
      IL_0046:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_004b:  stloc.1
      IL_004c:  ldc.i4.0
      IL_004d:  stloc.2
      IL_004e:  newobj     instance void Studio.Info/LightLoadInfo::.ctor()
      IL_0053:  stloc.3
      IL_0054:  ldloc.3
      IL_0055:  ldloc.1
      IL_0056:  ldloc.2
      IL_0057:  dup
      IL_0058:  ldc.i4.1
      IL_0059:  add
      IL_005a:  stloc.2
      IL_005b:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0060:  call       int32 [mscorlib]System.Int32::Parse(string)
      IL_0065:  stfld      int32 Studio.Info/LightLoadInfo::no
      IL_006a:  ldloc.3
      IL_006b:  ldloc.1
      IL_006c:  ldloc.2
      IL_006d:  dup
      IL_006e:  ldc.i4.1
      IL_006f:  add
      IL_0070:  stloc.2
      IL_0071:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0076:  stfld      string Studio.Info/LoadCommonInfo::name
      IL_007b:  ldloc.3
      IL_007c:  ldloc.1
      IL_007d:  ldloc.2
      IL_007e:  dup
      IL_007f:  ldc.i4.1
      IL_0080:  add
      IL_0081:  stloc.2
      IL_0082:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0087:  stfld      string Studio.Info/FileInfo::manifest
      IL_008c:  ldloc.3
      IL_008d:  ldloc.1
      IL_008e:  ldloc.2
      IL_008f:  dup
      IL_0090:  ldc.i4.1
      IL_0091:  add
      IL_0092:  stloc.2
      IL_0093:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0098:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_009d:  ldloc.3
      IL_009e:  ldloc.1
      IL_009f:  ldloc.2
      IL_00a0:  dup
      IL_00a1:  ldc.i4.1
      IL_00a2:  add
      IL_00a3:  stloc.2
      IL_00a4:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_00a9:  stfld      string Studio.Info/FileInfo::fileName
      IL_00ae:  ldloc.3
      IL_00af:  ldloc.1
      IL_00b0:  ldloc.2
      IL_00b1:  dup
      IL_00b2:  ldc.i4.1
      IL_00b3:  add
      IL_00b4:  stloc.2
      IL_00b5:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_00ba:  call       int32 [mscorlib]System.Int32::Parse(string)
      IL_00bf:  stfld      valuetype Studio.Info/LightLoadInfo/Target Studio.Info/LightLoadInfo::target
      IL_00c4:  ldarg.0
      IL_00c5:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LightLoadInfo> Studio.Info::dicLightLoadInfo
      IL_00ca:  ldloc.3
      IL_00cb:  ldfld      int32 Studio.Info/LightLoadInfo::no
      IL_00d0:  ldloc.3
      IL_00d1:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LightLoadInfo>::set_Item(!0,
                                                                                                                                                  !1)
      IL_00d6:  ldloc.0
      IL_00d7:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00dc:  brtrue     IL_0045

      IL_00e1:  leave.s    IL_00ed

    }  // end .try
    finally
    {
      IL_00e3:  ldloc.0
      IL_00e4:  brfalse.s  IL_00ec

      IL_00e6:  ldloc.0
      IL_00e7:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00ec:  endfinally
    }  // end handler
    IL_00ed:  ret
  } // end of method Info::LoadLightLoadInfo

  .method private hidebysig instance void 
          LoadAnimeGroupInfo(class [IL]ExcelData _ed,
                             class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> _dic) cil managed
  {
    // 代码大小       235 (0xeb)
    .maxstack  4
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             int32 V_3,
             int32 V_4,
             string V_5,
             class Studio.Info/GroupInfo V_6)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.1
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__78_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadAnimeGroupInfo>b__78_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__78_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br         IL_00d3

      IL_0045:  ldloc.0
      IL_0046:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_004b:  stloc.1
      IL_004c:  ldc.i4.0
      IL_004d:  stloc.2
      IL_004e:  ldc.i4.0
      IL_004f:  stloc.3
      IL_0050:  ldloc.1
      IL_0051:  ldloc.2
      IL_0052:  dup
      IL_0053:  ldc.i4.1
      IL_0054:  add
      IL_0055:  stloc.2
      IL_0056:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_005b:  ldloca.s   V_3
      IL_005d:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0062:  brfalse.s  IL_00d3

      IL_0064:  ldc.i4.m1
      IL_0065:  stloc.s    V_4
      IL_0067:  ldloc.1
      IL_0068:  ldloc.2
      IL_0069:  dup
      IL_006a:  ldc.i4.1
      IL_006b:  add
      IL_006c:  stloc.2
      IL_006d:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0072:  ldloca.s   V_4
      IL_0074:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0079:  brfalse.s  IL_00d3

      IL_007b:  ldloc.1
      IL_007c:  ldloc.2
      IL_007d:  dup
      IL_007e:  ldc.i4.1
      IL_007f:  add
      IL_0080:  stloc.2
      IL_0081:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0086:  stloc.s    V_5
      IL_0088:  ldnull
      IL_0089:  stloc.s    V_6
      IL_008b:  ldarg.2
      IL_008c:  ldloc.s    V_4
      IL_008e:  ldloca.s   V_6
      IL_0090:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::TryGetValue(!0,
                                                                                                                                                 !1&)
      IL_0095:  brfalse.s  IL_00aa

      IL_0097:  ldloc.s    V_6
      IL_0099:  ldloc.3
      IL_009a:  stfld      int32 Studio.Info/GroupInfo::sort
      IL_009f:  ldloc.s    V_6
      IL_00a1:  ldloc.s    V_5
      IL_00a3:  stfld      string Studio.Info/GroupInfo::name
      IL_00a8:  br.s       IL_00d3

      IL_00aa:  newobj     instance void Studio.Info/GroupInfo::.ctor()
      IL_00af:  dup
      IL_00b0:  ldloc.3
      IL_00b1:  stfld      int32 Studio.Info/GroupInfo::sort
      IL_00b6:  dup
      IL_00b7:  ldloc.s    V_5
      IL_00b9:  stfld      string Studio.Info/GroupInfo::name
      IL_00be:  stloc.s    V_6
      IL_00c0:  ldloc.s    V_6
      IL_00c2:  ldloc.s    V_5
      IL_00c4:  stfld      string Studio.Info/GroupInfo::name
      IL_00c9:  ldarg.2
      IL_00ca:  ldloc.s    V_4
      IL_00cc:  ldloc.s    V_6
      IL_00ce:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::Add(!0,
                                                                                                                                         !1)
      IL_00d3:  ldloc.0
      IL_00d4:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00d9:  brtrue     IL_0045

      IL_00de:  leave.s    IL_00ea

    }  // end .try
    finally
    {
      IL_00e0:  ldloc.0
      IL_00e1:  brfalse.s  IL_00e9

      IL_00e3:  ldloc.0
      IL_00e4:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00e9:  endfinally
    }  // end handler
    IL_00ea:  ret
  } // end of method Info::LoadAnimeGroupInfo

  .method private hidebysig instance void 
          LoadAnimeCategoryInfo(string _bundlePath,
                                string _regex,
                                class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> _dic) cil managed
  {
    // 代码大小       360 (0x168)
    .maxstack  5
    .locals init (string V_0,
             string[] V_1,
             string V_2,
             class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_3,
             int32 V_4,
             int32 V_5,
             int32 V_6,
             valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_7,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_8,
             valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> V_9,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string> V_10)
    IL_0000:  ldstr      ""
    IL_0005:  stloc.0
    IL_0006:  ldarg.0
    IL_0007:  ldarg.1
    IL_0008:  ldarg.2
    IL_0009:  ldloca.s   V_0
    IL_000b:  call       instance string[] Studio.Info::FindAllAssetName(string,
                                                                         string,
                                                                         string&)
    IL_0010:  stloc.1
    IL_0011:  ldloc.1
    IL_0012:  call       bool [IL]NullCheck::IsNullOrEmpty<string>(class [mscorlib]System.Collections.Generic.IReadOnlyCollection`1<!!0>)
    IL_0017:  brfalse.s  IL_001a

    IL_0019:  ret

    IL_001a:  ldarg.2
    IL_001b:  ldc.i4.1
    IL_001c:  newarr     [mscorlib]System.Char
    IL_0021:  dup
    IL_0022:  ldc.i4.0
    IL_0023:  ldc.i4.s   95
    IL_0025:  stelem.i2
    IL_0026:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
    IL_002b:  ldc.i4.0
    IL_002c:  ldelem.ref
    IL_002d:  callvirt   instance string [mscorlib]System.String::ToLower()
    IL_0032:  stloc.2
    IL_0033:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::.ctor()
    IL_0038:  stloc.3
    IL_0039:  ldc.i4.0
    IL_003a:  stloc.s    V_4
    IL_003c:  br         IL_00ce

    IL_0041:  ldloc.1
    IL_0042:  ldloc.s    V_4
    IL_0044:  ldelem.ref
    IL_0045:  ldc.i4.1
    IL_0046:  newarr     [mscorlib]System.Char
    IL_004b:  dup
    IL_004c:  ldc.i4.0
    IL_004d:  ldc.i4.s   95
    IL_004f:  stelem.i2
    IL_0050:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
    IL_0055:  ldc.i4.0
    IL_0056:  ldelem.ref
    IL_0057:  callvirt   instance string [mscorlib]System.String::ToLower()
    IL_005c:  ldloc.2
    IL_005d:  callvirt   instance int32 [mscorlib]System.String::CompareTo(string)
    IL_0062:  brtrue.s   IL_00c8

    IL_0064:  ldloc.1
    IL_0065:  ldloc.s    V_4
    IL_0067:  ldelem.ref
    IL_0068:  ldarg.2
    IL_0069:  ldc.i4.1
    IL_006a:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                string,
                                                                                                                                valuetype [System]System.Text.RegularExpressions.RegexOptions)
    IL_006f:  dup
    IL_0070:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
    IL_0075:  ldc.i4.1
    IL_0076:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
    IL_007b:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
    IL_0080:  call       int32 [mscorlib]System.Int32::Parse(string)
    IL_0085:  stloc.s    V_5
    IL_0087:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
    IL_008c:  ldc.i4.2
    IL_008d:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
    IL_0092:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
    IL_0097:  call       int32 [mscorlib]System.Int32::Parse(string)
    IL_009c:  stloc.s    V_6
    IL_009e:  ldloc.3
    IL_009f:  ldloc.s    V_6
    IL_00a1:  callvirt   instance bool class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::ContainsKey(!0)
    IL_00a6:  brtrue.s   IL_00b5

    IL_00a8:  ldloc.3
    IL_00a9:  ldloc.s    V_6
    IL_00ab:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::.ctor()
    IL_00b0:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::Add(!0,
                                                                                                                                                                                         !1)
    IL_00b5:  ldloc.3
    IL_00b6:  ldloc.s    V_6
    IL_00b8:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Item(!0)
    IL_00bd:  ldloc.s    V_5
    IL_00bf:  ldloc.1
    IL_00c0:  ldloc.s    V_4
    IL_00c2:  ldelem.ref
    IL_00c3:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::Add(!0,
                                                                                                                      !1)
    IL_00c8:  ldloc.s    V_4
    IL_00ca:  ldc.i4.1
    IL_00cb:  add
    IL_00cc:  stloc.s    V_4
    IL_00ce:  ldloc.s    V_4
    IL_00d0:  ldloc.1
    IL_00d1:  ldlen
    IL_00d2:  conv.i4
    IL_00d3:  blt        IL_0041

    IL_00d8:  ldloc.3
    IL_00d9:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::GetEnumerator()
    IL_00de:  stloc.s    V_7
    .try
    {
      IL_00e0:  br.s       IL_014e

      IL_00e2:  ldloca.s   V_7
      IL_00e4:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Current()
      IL_00e9:  stloc.s    V_8
      IL_00eb:  ldarg.3
      IL_00ec:  ldloca.s   V_8
      IL_00ee:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Key()
      IL_00f3:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::ContainsKey(!0)
      IL_00f8:  brfalse.s  IL_014e

      IL_00fa:  ldloca.s   V_8
      IL_00fc:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Value()
      IL_0101:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::GetEnumerator()
      IL_0106:  stloc.s    V_9
      .try
      {
        IL_0108:  br.s       IL_0135

        IL_010a:  ldloca.s   V_9
        IL_010c:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::get_Current()
        IL_0111:  stloc.s    V_10
        IL_0113:  ldarg.0
        IL_0114:  ldarg.0
        IL_0115:  ldarg.1
        IL_0116:  ldloca.s   V_10
        IL_0118:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string>::get_Value()
        IL_011d:  ldloc.0
        IL_011e:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                     string,
                                                                                     string)
        IL_0123:  ldarg.3
        IL_0124:  ldloca.s   V_8
        IL_0126:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Key()
        IL_012b:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::get_Item(!0)
        IL_0130:  call       instance void Studio.Info::LoadAnimeCategoryInfo(class [IL]ExcelData,
                                                                              class Studio.Info/GroupInfo)
        IL_0135:  ldloca.s   V_9
        IL_0137:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::MoveNext()
        IL_013c:  brtrue.s   IL_010a

        IL_013e:  leave.s    IL_014e

      }  // end .try
      finally
      {
        IL_0140:  ldloca.s   V_9
        IL_0142:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>
        IL_0148:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
        IL_014d:  endfinally
      }  // end handler
      IL_014e:  ldloca.s   V_7
      IL_0150:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::MoveNext()
      IL_0155:  brtrue.s   IL_00e2

      IL_0157:  leave.s    IL_0167

    }  // end .try
    finally
    {
      IL_0159:  ldloca.s   V_7
      IL_015b:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>
      IL_0161:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0166:  endfinally
    }  // end handler
    IL_0167:  ret
  } // end of method Info::LoadAnimeCategoryInfo

  .method private hidebysig instance void 
          LoadAnimeCategoryInfo(class [IL]ExcelData _ed,
                                class Studio.Info/GroupInfo _info) cil managed
  {
    // 代码大小       183 (0xb7)
    .maxstack  8
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             int32 V_3,
             int32 V_4)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.1
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__80_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadAnimeCategoryInfo>b__80_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__80_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br.s       IL_00a2

      IL_0042:  ldloc.0
      IL_0043:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_0048:  stloc.1
      IL_0049:  ldc.i4.0
      IL_004a:  stloc.2
      IL_004b:  ldc.i4.0
      IL_004c:  stloc.3
      IL_004d:  ldloc.1
      IL_004e:  ldloc.2
      IL_004f:  dup
      IL_0050:  ldc.i4.1
      IL_0051:  add
      IL_0052:  stloc.2
      IL_0053:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0058:  ldloca.s   V_3
      IL_005a:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_005f:  brfalse.s  IL_00a2

      IL_0061:  ldc.i4.m1
      IL_0062:  stloc.s    V_4
      IL_0064:  ldloc.1
      IL_0065:  ldloc.2
      IL_0066:  dup
      IL_0067:  ldc.i4.1
      IL_0068:  add
      IL_0069:  stloc.2
      IL_006a:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_006f:  ldloca.s   V_4
      IL_0071:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0076:  brfalse.s  IL_00a2

      IL_0078:  ldarg.2
      IL_0079:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/CategoryInfo> Studio.Info/GroupInfo::dicCategory
      IL_007e:  ldloc.s    V_4
      IL_0080:  newobj     instance void Studio.Info/CategoryInfo::.ctor()
      IL_0085:  dup
      IL_0086:  ldloc.3
      IL_0087:  stfld      int32 Studio.Info/CategoryInfo::sort
      IL_008c:  dup
      IL_008d:  ldloc.1
      IL_008e:  ldloc.2
      IL_008f:  dup
      IL_0090:  ldc.i4.1
      IL_0091:  add
      IL_0092:  stloc.2
      IL_0093:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0098:  stfld      string Studio.Info/CategoryInfo::name
      IL_009d:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/CategoryInfo>::set_Item(!0,
                                                                                                                                                 !1)
      IL_00a2:  ldloc.0
      IL_00a3:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00a8:  brtrue.s   IL_0042

      IL_00aa:  leave.s    IL_00b6

    }  // end .try
    finally
    {
      IL_00ac:  ldloc.0
      IL_00ad:  brfalse.s  IL_00b5

      IL_00af:  ldloc.0
      IL_00b0:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00b5:  endfinally
    }  // end handler
    IL_00b6:  ret
  } // end of method Info::LoadAnimeCategoryInfo

  .method private hidebysig instance void 
          LoadItemGroupInfo(class [IL]ExcelData _ed) cil managed
  {
    // 代码大小       245 (0xf5)
    .maxstack  4
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             int32 V_3,
             int32 V_4,
             string V_5,
             class Studio.Info/GroupInfo V_6)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.1
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__81_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadItemGroupInfo>b__81_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__81_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br         IL_00dd

      IL_0045:  ldloc.0
      IL_0046:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_004b:  stloc.1
      IL_004c:  ldc.i4.0
      IL_004d:  stloc.2
      IL_004e:  ldc.i4.0
      IL_004f:  stloc.3
      IL_0050:  ldloc.1
      IL_0051:  ldloc.2
      IL_0052:  dup
      IL_0053:  ldc.i4.1
      IL_0054:  add
      IL_0055:  stloc.2
      IL_0056:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_005b:  ldloca.s   V_3
      IL_005d:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0062:  brfalse.s  IL_00dd

      IL_0064:  ldc.i4.m1
      IL_0065:  stloc.s    V_4
      IL_0067:  ldloc.1
      IL_0068:  ldloc.2
      IL_0069:  dup
      IL_006a:  ldc.i4.1
      IL_006b:  add
      IL_006c:  stloc.2
      IL_006d:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0072:  ldloca.s   V_4
      IL_0074:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0079:  brfalse.s  IL_00dd

      IL_007b:  ldloc.1
      IL_007c:  ldloc.2
      IL_007d:  dup
      IL_007e:  ldc.i4.1
      IL_007f:  add
      IL_0080:  stloc.2
      IL_0081:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0086:  stloc.s    V_5
      IL_0088:  ldnull
      IL_0089:  stloc.s    V_6
      IL_008b:  ldarg.0
      IL_008c:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicItemGroupCategory
      IL_0091:  ldloc.s    V_4
      IL_0093:  ldloca.s   V_6
      IL_0095:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::TryGetValue(!0,
                                                                                                                                                 !1&)
      IL_009a:  brfalse.s  IL_00af

      IL_009c:  ldloc.s    V_6
      IL_009e:  ldloc.3
      IL_009f:  stfld      int32 Studio.Info/GroupInfo::sort
      IL_00a4:  ldloc.s    V_6
      IL_00a6:  ldloc.s    V_5
      IL_00a8:  stfld      string Studio.Info/GroupInfo::name
      IL_00ad:  br.s       IL_00dd

      IL_00af:  newobj     instance void Studio.Info/GroupInfo::.ctor()
      IL_00b4:  dup
      IL_00b5:  ldloc.3
      IL_00b6:  stfld      int32 Studio.Info/GroupInfo::sort
      IL_00bb:  dup
      IL_00bc:  ldloc.s    V_5
      IL_00be:  stfld      string Studio.Info/GroupInfo::name
      IL_00c3:  stloc.s    V_6
      IL_00c5:  ldloc.s    V_6
      IL_00c7:  ldloc.s    V_5
      IL_00c9:  stfld      string Studio.Info/GroupInfo::name
      IL_00ce:  ldarg.0
      IL_00cf:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicItemGroupCategory
      IL_00d4:  ldloc.s    V_4
      IL_00d6:  ldloc.s    V_6
      IL_00d8:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::Add(!0,
                                                                                                                                         !1)
      IL_00dd:  ldloc.0
      IL_00de:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00e3:  brtrue     IL_0045

      IL_00e8:  leave.s    IL_00f4

    }  // end .try
    finally
    {
      IL_00ea:  ldloc.0
      IL_00eb:  brfalse.s  IL_00f3

      IL_00ed:  ldloc.0
      IL_00ee:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00f3:  endfinally
    }  // end handler
    IL_00f4:  ret
  } // end of method Info::LoadItemGroupInfo

  .method private hidebysig instance void 
          LoadItemCategoryInfo(string _bundlePath,
                               string _regex) cil managed
  {
    // 代码大小       359 (0x167)
    .maxstack  5
    .locals init (string V_0,
             string[] V_1,
             string V_2,
             class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_3,
             int32 V_4,
             int32 V_5,
             int32 V_6,
             valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_7,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_8,
             valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> V_9,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string> V_10)
    IL_0000:  ldstr      ""
    IL_0005:  stloc.0
    IL_0006:  ldarg.0
    IL_0007:  ldarg.1
    IL_0008:  ldarg.2
    IL_0009:  ldloca.s   V_0
    IL_000b:  call       instance string[] Studio.Info::FindAllAssetName(string,
                                                                         string,
                                                                         string&)
    IL_0010:  stloc.1
    IL_0011:  ldloc.1
    IL_0012:  call       bool [IL]NullCheck::IsNullOrEmpty<string>(class [mscorlib]System.Collections.Generic.IReadOnlyCollection`1<!!0>)
    IL_0017:  brfalse.s  IL_001a

    IL_0019:  ret

    IL_001a:  ldarg.2
    IL_001b:  ldc.i4.1
    IL_001c:  newarr     [mscorlib]System.Char
    IL_0021:  dup
    IL_0022:  ldc.i4.0
    IL_0023:  ldc.i4.s   95
    IL_0025:  stelem.i2
    IL_0026:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
    IL_002b:  ldc.i4.0
    IL_002c:  ldelem.ref
    IL_002d:  callvirt   instance string [mscorlib]System.String::ToLower()
    IL_0032:  stloc.2
    IL_0033:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::.ctor()
    IL_0038:  stloc.3
    IL_0039:  ldc.i4.0
    IL_003a:  stloc.s    V_4
    IL_003c:  br         IL_00ce

    IL_0041:  ldloc.1
    IL_0042:  ldloc.s    V_4
    IL_0044:  ldelem.ref
    IL_0045:  ldc.i4.1
    IL_0046:  newarr     [mscorlib]System.Char
    IL_004b:  dup
    IL_004c:  ldc.i4.0
    IL_004d:  ldc.i4.s   95
    IL_004f:  stelem.i2
    IL_0050:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
    IL_0055:  ldc.i4.0
    IL_0056:  ldelem.ref
    IL_0057:  callvirt   instance string [mscorlib]System.String::ToLower()
    IL_005c:  ldloc.2
    IL_005d:  callvirt   instance int32 [mscorlib]System.String::CompareTo(string)
    IL_0062:  brtrue.s   IL_00c8

    IL_0064:  ldloc.1
    IL_0065:  ldloc.s    V_4
    IL_0067:  ldelem.ref
    IL_0068:  ldarg.2
    IL_0069:  ldc.i4.1
    IL_006a:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                string,
                                                                                                                                valuetype [System]System.Text.RegularExpressions.RegexOptions)
    IL_006f:  dup
    IL_0070:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
    IL_0075:  ldc.i4.1
    IL_0076:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
    IL_007b:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
    IL_0080:  call       int32 [mscorlib]System.Int32::Parse(string)
    IL_0085:  stloc.s    V_5
    IL_0087:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
    IL_008c:  ldc.i4.2
    IL_008d:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
    IL_0092:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
    IL_0097:  call       int32 [mscorlib]System.Int32::Parse(string)
    IL_009c:  stloc.s    V_6
    IL_009e:  ldloc.3
    IL_009f:  ldloc.s    V_6
    IL_00a1:  callvirt   instance bool class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::ContainsKey(!0)
    IL_00a6:  brtrue.s   IL_00b5

    IL_00a8:  ldloc.3
    IL_00a9:  ldloc.s    V_6
    IL_00ab:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::.ctor()
    IL_00b0:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::Add(!0,
                                                                                                                                                                                         !1)
    IL_00b5:  ldloc.3
    IL_00b6:  ldloc.s    V_6
    IL_00b8:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Item(!0)
    IL_00bd:  ldloc.s    V_5
    IL_00bf:  ldloc.1
    IL_00c0:  ldloc.s    V_4
    IL_00c2:  ldelem.ref
    IL_00c3:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::Add(!0,
                                                                                                                      !1)
    IL_00c8:  ldloc.s    V_4
    IL_00ca:  ldc.i4.1
    IL_00cb:  add
    IL_00cc:  stloc.s    V_4
    IL_00ce:  ldloc.s    V_4
    IL_00d0:  ldloc.1
    IL_00d1:  ldlen
    IL_00d2:  conv.i4
    IL_00d3:  blt        IL_0041

    IL_00d8:  ldloc.3
    IL_00d9:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::GetEnumerator()
    IL_00de:  stloc.s    V_7
    .try
    {
      IL_00e0:  br.s       IL_014d

      IL_00e2:  ldloca.s   V_7
      IL_00e4:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Current()
      IL_00e9:  stloc.s    V_8
      IL_00eb:  ldarg.0
      IL_00ec:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicItemGroupCategory
      IL_00f1:  ldloca.s   V_8
      IL_00f3:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Key()
      IL_00f8:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::ContainsKey(!0)
      IL_00fd:  brfalse.s  IL_014d

      IL_00ff:  ldloca.s   V_8
      IL_0101:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Value()
      IL_0106:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::GetEnumerator()
      IL_010b:  stloc.s    V_9
      .try
      {
        IL_010d:  br.s       IL_0134

        IL_010f:  ldloca.s   V_9
        IL_0111:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::get_Current()
        IL_0116:  stloc.s    V_10
        IL_0118:  ldarg.0
        IL_0119:  ldarg.0
        IL_011a:  ldarg.1
        IL_011b:  ldloca.s   V_10
        IL_011d:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string>::get_Value()
        IL_0122:  ldloc.0
        IL_0123:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                     string,
                                                                                     string)
        IL_0128:  ldloca.s   V_8
        IL_012a:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Key()
        IL_012f:  call       instance void Studio.Info::LoadItemCategoryInfo(class [IL]ExcelData,
                                                                             int32)
        IL_0134:  ldloca.s   V_9
        IL_0136:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::MoveNext()
        IL_013b:  brtrue.s   IL_010f

        IL_013d:  leave.s    IL_014d

      }  // end .try
      finally
      {
        IL_013f:  ldloca.s   V_9
        IL_0141:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>
        IL_0147:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
        IL_014c:  endfinally
      }  // end handler
      IL_014d:  ldloca.s   V_7
      IL_014f:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::MoveNext()
      IL_0154:  brtrue.s   IL_00e2

      IL_0156:  leave.s    IL_0166

    }  // end .try
    finally
    {
      IL_0158:  ldloca.s   V_7
      IL_015a:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>
      IL_0160:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0165:  endfinally
    }  // end handler
    IL_0166:  ret
  } // end of method Info::LoadItemCategoryInfo

  .method private hidebysig instance void 
          LoadItemCategoryInfo(class [IL]ExcelData _ed,
                               int32 _group) cil managed
  {
    // 代码大小       198 (0xc6)
    .maxstack  8
    .locals init (class Studio.Info/GroupInfo V_0,
             class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_1,
             class [mscorlib]System.Collections.Generic.List`1<string> V_2,
             int32 V_3,
             int32 V_4,
             int32 V_5)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.0
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicItemGroupCategory
    IL_0010:  ldarg.2
    IL_0011:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::get_Item(!0)
    IL_0016:  stloc.0
    IL_0017:  ldarg.1
    IL_0018:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_001d:  ldc.i4.1
    IL_001e:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0023:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__83_0'
    IL_0028:  dup
    IL_0029:  brtrue.s   IL_0042

    IL_002b:  pop
    IL_002c:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0031:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadItemCategoryInfo>b__83_0'(class [IL]ExcelData/Param)
    IL_0037:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_003c:  dup
    IL_003d:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__83_0'
    IL_0042:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_0047:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_004c:  stloc.1
    .try
    {
      IL_004d:  br.s       IL_00b1

      IL_004f:  ldloc.1
      IL_0050:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_0055:  stloc.2
      IL_0056:  ldc.i4.0
      IL_0057:  stloc.3
      IL_0058:  ldc.i4.0
      IL_0059:  stloc.s    V_4
      IL_005b:  ldloc.2
      IL_005c:  ldloc.3
      IL_005d:  dup
      IL_005e:  ldc.i4.1
      IL_005f:  add
      IL_0060:  stloc.3
      IL_0061:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0066:  ldloca.s   V_4
      IL_0068:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_006d:  brfalse.s  IL_00b1

      IL_006f:  ldc.i4.m1
      IL_0070:  stloc.s    V_5
      IL_0072:  ldloc.2
      IL_0073:  ldloc.3
      IL_0074:  dup
      IL_0075:  ldc.i4.1
      IL_0076:  add
      IL_0077:  stloc.3
      IL_0078:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_007d:  ldloca.s   V_5
      IL_007f:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0084:  brfalse.s  IL_00b1

      IL_0086:  ldloc.0
      IL_0087:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/CategoryInfo> Studio.Info/GroupInfo::dicCategory
      IL_008c:  ldloc.s    V_5
      IL_008e:  newobj     instance void Studio.Info/CategoryInfo::.ctor()
      IL_0093:  dup
      IL_0094:  ldloc.s    V_4
      IL_0096:  stfld      int32 Studio.Info/CategoryInfo::sort
      IL_009b:  dup
      IL_009c:  ldloc.2
      IL_009d:  ldloc.3
      IL_009e:  dup
      IL_009f:  ldc.i4.1
      IL_00a0:  add
      IL_00a1:  stloc.3
      IL_00a2:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_00a7:  stfld      string Studio.Info/CategoryInfo::name
      IL_00ac:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/CategoryInfo>::set_Item(!0,
                                                                                                                                                 !1)
      IL_00b1:  ldloc.1
      IL_00b2:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00b7:  brtrue.s   IL_004f

      IL_00b9:  leave.s    IL_00c5

    }  // end .try
    finally
    {
      IL_00bb:  ldloc.1
      IL_00bc:  brfalse.s  IL_00c4

      IL_00be:  ldloc.1
      IL_00bf:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00c4:  endfinally
    }  // end handler
    IL_00c5:  ret
  } // end of method Info::LoadItemCategoryInfo

  .method private hidebysig instance void 
          LoadAnimeGroupInfo(class [IL]ExcelData _ed) cil managed
  {
    // 代码大小       236 (0xec)
    .maxstack  4
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             int32 V_3,
             int32 V_4,
             string V_5,
             class Studio.Info/GroupInfo V_6)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.1
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__84_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadAnimeGroupInfo>b__84_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__84_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br         IL_00d4

      IL_0045:  ldloc.0
      IL_0046:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_004b:  stloc.1
      IL_004c:  ldc.i4.0
      IL_004d:  stloc.2
      IL_004e:  ldc.i4.0
      IL_004f:  stloc.3
      IL_0050:  ldloc.1
      IL_0051:  ldloc.2
      IL_0052:  dup
      IL_0053:  ldc.i4.1
      IL_0054:  add
      IL_0055:  stloc.2
      IL_0056:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_005b:  ldloca.s   V_3
      IL_005d:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0062:  brfalse.s  IL_00d4

      IL_0064:  ldc.i4.m1
      IL_0065:  stloc.s    V_4
      IL_0067:  ldloc.1
      IL_0068:  ldloc.2
      IL_0069:  dup
      IL_006a:  ldc.i4.1
      IL_006b:  add
      IL_006c:  stloc.2
      IL_006d:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0072:  ldloca.s   V_4
      IL_0074:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0079:  brfalse.s  IL_00d4

      IL_007b:  ldloc.1
      IL_007c:  ldloc.2
      IL_007d:  dup
      IL_007e:  ldc.i4.1
      IL_007f:  add
      IL_0080:  stloc.2
      IL_0081:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0086:  stloc.s    V_5
      IL_0088:  ldnull
      IL_0089:  stloc.s    V_6
      IL_008b:  ldarg.0
      IL_008c:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicAGroupCategory
      IL_0091:  ldloc.s    V_4
      IL_0093:  ldloca.s   V_6
      IL_0095:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::TryGetValue(!0,
                                                                                                                                                 !1&)
      IL_009a:  brfalse.s  IL_00af

      IL_009c:  ldloc.s    V_6
      IL_009e:  ldloc.3
      IL_009f:  stfld      int32 Studio.Info/GroupInfo::sort
      IL_00a4:  ldloc.s    V_6
      IL_00a6:  ldloc.s    V_5
      IL_00a8:  stfld      string Studio.Info/GroupInfo::name
      IL_00ad:  br.s       IL_00d4

      IL_00af:  newobj     instance void Studio.Info/GroupInfo::.ctor()
      IL_00b4:  dup
      IL_00b5:  ldloc.3
      IL_00b6:  stfld      int32 Studio.Info/GroupInfo::sort
      IL_00bb:  dup
      IL_00bc:  ldloc.s    V_5
      IL_00be:  stfld      string Studio.Info/GroupInfo::name
      IL_00c3:  stloc.s    V_6
      IL_00c5:  ldarg.0
      IL_00c6:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicAGroupCategory
      IL_00cb:  ldloc.s    V_4
      IL_00cd:  ldloc.s    V_6
      IL_00cf:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::Add(!0,
                                                                                                                                         !1)
      IL_00d4:  ldloc.0
      IL_00d5:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00da:  brtrue     IL_0045

      IL_00df:  leave.s    IL_00eb

    }  // end .try
    finally
    {
      IL_00e1:  ldloc.0
      IL_00e2:  brfalse.s  IL_00ea

      IL_00e4:  ldloc.0
      IL_00e5:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00ea:  endfinally
    }  // end handler
    IL_00eb:  ret
  } // end of method Info::LoadAnimeGroupInfo

  .method private hidebysig instance void 
          LoadAnimeCategoryInfo(string _bundlePath,
                                string _regex) cil managed
  {
    // 代码大小       359 (0x167)
    .maxstack  5
    .locals init (string V_0,
             string[] V_1,
             string V_2,
             class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_3,
             int32 V_4,
             int32 V_5,
             int32 V_6,
             valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_7,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>> V_8,
             valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string> V_9,
             valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string> V_10)
    IL_0000:  ldstr      ""
    IL_0005:  stloc.0
    IL_0006:  ldarg.0
    IL_0007:  ldarg.1
    IL_0008:  ldarg.2
    IL_0009:  ldloca.s   V_0
    IL_000b:  call       instance string[] Studio.Info::FindAllAssetName(string,
                                                                         string,
                                                                         string&)
    IL_0010:  stloc.1
    IL_0011:  ldloc.1
    IL_0012:  call       bool [IL]NullCheck::IsNullOrEmpty<string>(class [mscorlib]System.Collections.Generic.IReadOnlyCollection`1<!!0>)
    IL_0017:  brfalse.s  IL_001a

    IL_0019:  ret

    IL_001a:  ldarg.2
    IL_001b:  ldc.i4.1
    IL_001c:  newarr     [mscorlib]System.Char
    IL_0021:  dup
    IL_0022:  ldc.i4.0
    IL_0023:  ldc.i4.s   95
    IL_0025:  stelem.i2
    IL_0026:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
    IL_002b:  ldc.i4.0
    IL_002c:  ldelem.ref
    IL_002d:  callvirt   instance string [mscorlib]System.String::ToLower()
    IL_0032:  stloc.2
    IL_0033:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::.ctor()
    IL_0038:  stloc.3
    IL_0039:  ldc.i4.0
    IL_003a:  stloc.s    V_4
    IL_003c:  br         IL_00ce

    IL_0041:  ldloc.1
    IL_0042:  ldloc.s    V_4
    IL_0044:  ldelem.ref
    IL_0045:  ldc.i4.1
    IL_0046:  newarr     [mscorlib]System.Char
    IL_004b:  dup
    IL_004c:  ldc.i4.0
    IL_004d:  ldc.i4.s   95
    IL_004f:  stelem.i2
    IL_0050:  callvirt   instance string[] [mscorlib]System.String::Split(char[])
    IL_0055:  ldc.i4.0
    IL_0056:  ldelem.ref
    IL_0057:  callvirt   instance string [mscorlib]System.String::ToLower()
    IL_005c:  ldloc.2
    IL_005d:  callvirt   instance int32 [mscorlib]System.String::CompareTo(string)
    IL_0062:  brtrue.s   IL_00c8

    IL_0064:  ldloc.1
    IL_0065:  ldloc.s    V_4
    IL_0067:  ldelem.ref
    IL_0068:  ldarg.2
    IL_0069:  ldc.i4.1
    IL_006a:  call       class [System]System.Text.RegularExpressions.Match [System]System.Text.RegularExpressions.Regex::Match(string,
                                                                                                                                string,
                                                                                                                                valuetype [System]System.Text.RegularExpressions.RegexOptions)
    IL_006f:  dup
    IL_0070:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
    IL_0075:  ldc.i4.1
    IL_0076:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
    IL_007b:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
    IL_0080:  call       int32 [mscorlib]System.Int32::Parse(string)
    IL_0085:  stloc.s    V_5
    IL_0087:  callvirt   instance class [System]System.Text.RegularExpressions.GroupCollection [System]System.Text.RegularExpressions.Match::get_Groups()
    IL_008c:  ldc.i4.2
    IL_008d:  callvirt   instance class [System]System.Text.RegularExpressions.Group [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
    IL_0092:  callvirt   instance string [System]System.Text.RegularExpressions.Capture::get_Value()
    IL_0097:  call       int32 [mscorlib]System.Int32::Parse(string)
    IL_009c:  stloc.s    V_6
    IL_009e:  ldloc.3
    IL_009f:  ldloc.s    V_6
    IL_00a1:  callvirt   instance bool class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::ContainsKey(!0)
    IL_00a6:  brtrue.s   IL_00b5

    IL_00a8:  ldloc.3
    IL_00a9:  ldloc.s    V_6
    IL_00ab:  newobj     instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::.ctor()
    IL_00b0:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::Add(!0,
                                                                                                                                                                                         !1)
    IL_00b5:  ldloc.3
    IL_00b6:  ldloc.s    V_6
    IL_00b8:  callvirt   instance !1 class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Item(!0)
    IL_00bd:  ldloc.s    V_5
    IL_00bf:  ldloc.1
    IL_00c0:  ldloc.s    V_4
    IL_00c2:  ldelem.ref
    IL_00c3:  callvirt   instance void class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::Add(!0,
                                                                                                                      !1)
    IL_00c8:  ldloc.s    V_4
    IL_00ca:  ldc.i4.1
    IL_00cb:  add
    IL_00cc:  stloc.s    V_4
    IL_00ce:  ldloc.s    V_4
    IL_00d0:  ldloc.1
    IL_00d1:  ldlen
    IL_00d2:  conv.i4
    IL_00d3:  blt        IL_0041

    IL_00d8:  ldloc.3
    IL_00d9:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::GetEnumerator()
    IL_00de:  stloc.s    V_7
    .try
    {
      IL_00e0:  br.s       IL_014d

      IL_00e2:  ldloca.s   V_7
      IL_00e4:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Current()
      IL_00e9:  stloc.s    V_8
      IL_00eb:  ldarg.0
      IL_00ec:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicAGroupCategory
      IL_00f1:  ldloca.s   V_8
      IL_00f3:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Key()
      IL_00f8:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::ContainsKey(!0)
      IL_00fd:  brfalse.s  IL_014d

      IL_00ff:  ldloca.s   V_8
      IL_0101:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Value()
      IL_0106:  callvirt   instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<int32,string>::GetEnumerator()
      IL_010b:  stloc.s    V_9
      .try
      {
        IL_010d:  br.s       IL_0134

        IL_010f:  ldloca.s   V_9
        IL_0111:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::get_Current()
        IL_0116:  stloc.s    V_10
        IL_0118:  ldarg.0
        IL_0119:  ldarg.0
        IL_011a:  ldarg.1
        IL_011b:  ldloca.s   V_10
        IL_011d:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,string>::get_Value()
        IL_0122:  ldloc.0
        IL_0123:  call       instance class [IL]ExcelData Studio.Info::LoadExcelData(string,
                                                                                     string,
                                                                                     string)
        IL_0128:  ldloca.s   V_8
        IL_012a:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::get_Key()
        IL_012f:  call       instance void Studio.Info::LoadAnimeCategoryInfo(class [IL]ExcelData,
                                                                              int32)
        IL_0134:  ldloca.s   V_9
        IL_0136:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>::MoveNext()
        IL_013b:  brtrue.s   IL_010f

        IL_013d:  leave.s    IL_014d

      }  // end .try
      finally
      {
        IL_013f:  ldloca.s   V_9
        IL_0141:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,string>
        IL_0147:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
        IL_014c:  endfinally
      }  // end handler
      IL_014d:  ldloca.s   V_7
      IL_014f:  call       instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>::MoveNext()
      IL_0154:  brtrue.s   IL_00e2

      IL_0156:  leave.s    IL_0166

    }  // end .try
    finally
    {
      IL_0158:  ldloca.s   V_7
      IL_015a:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<int32,class [System]System.Collections.Generic.SortedDictionary`2<int32,string>>
      IL_0160:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0165:  endfinally
    }  // end handler
    IL_0166:  ret
  } // end of method Info::LoadAnimeCategoryInfo

  .method private hidebysig instance void 
          LoadAnimeCategoryInfo(class [IL]ExcelData _ed,
                                int32 _group) cil managed
  {
    // 代码大小       224 (0xe0)
    .maxstack  8
    .locals init (class Studio.Info/GroupInfo V_0,
             class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_1,
             class [mscorlib]System.Collections.Generic.List`1<string> V_2,
             int32 V_3,
             int32 V_4,
             int32 V_5)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.0
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicAGroupCategory
    IL_0010:  ldarg.2
    IL_0011:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::get_Item(!0)
    IL_0016:  stloc.0
    IL_0017:  ldarg.1
    IL_0018:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_001d:  ldc.i4.1
    IL_001e:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0023:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__86_0'
    IL_0028:  dup
    IL_0029:  brtrue.s   IL_0042

    IL_002b:  pop
    IL_002c:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0031:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadAnimeCategoryInfo>b__86_0'(class [IL]ExcelData/Param)
    IL_0037:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_003c:  dup
    IL_003d:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__86_0'
    IL_0042:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_0047:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_004c:  stloc.1
    .try
    {
      IL_004d:  br.s       IL_00c8

      IL_004f:  ldloc.1
      IL_0050:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_0055:  stloc.2
      IL_0056:  ldc.i4.0
      IL_0057:  stloc.3
      IL_0058:  ldc.i4.0
      IL_0059:  stloc.s    V_4
      IL_005b:  ldloc.2
      IL_005c:  ldloc.3
      IL_005d:  dup
      IL_005e:  ldc.i4.1
      IL_005f:  add
      IL_0060:  stloc.3
      IL_0061:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0066:  ldloca.s   V_4
      IL_0068:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_006d:  brfalse.s  IL_00c8

      IL_006f:  ldc.i4.m1
      IL_0070:  stloc.s    V_5
      IL_0072:  ldloc.2
      IL_0073:  ldloc.3
      IL_0074:  dup
      IL_0075:  ldc.i4.1
      IL_0076:  add
      IL_0077:  stloc.3
      IL_0078:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_007d:  ldloca.s   V_5
      IL_007f:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0084:  brfalse.s  IL_00c8

      IL_0086:  ldarg.2
      IL_0087:  brtrue.s   IL_009d

      IL_0089:  ldc.i4.1
      IL_008a:  ldloc.s    V_5
      IL_008c:  ldc.i4.s   12
      IL_008e:  call       bool [IL]MathfEx::RangeEqualOn<int32>(!!0,
                                                                 !!0,
                                                                 !!0)
      IL_0093:  brfalse.s  IL_009d

      IL_0095:  ldarg.0
      IL_0096:  call       instance bool Studio.Info::get_IsInstallAI()
      IL_009b:  brfalse.s  IL_00c8

      IL_009d:  ldloc.0
      IL_009e:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/CategoryInfo> Studio.Info/GroupInfo::dicCategory
      IL_00a3:  ldloc.s    V_5
      IL_00a5:  newobj     instance void Studio.Info/CategoryInfo::.ctor()
      IL_00aa:  dup
      IL_00ab:  ldloc.s    V_4
      IL_00ad:  stfld      int32 Studio.Info/CategoryInfo::sort
      IL_00b2:  dup
      IL_00b3:  ldloc.2
      IL_00b4:  ldloc.3
      IL_00b5:  dup
      IL_00b6:  ldc.i4.1
      IL_00b7:  add
      IL_00b8:  stloc.3
      IL_00b9:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_00be:  stfld      string Studio.Info/CategoryInfo::name
      IL_00c3:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/CategoryInfo>::set_Item(!0,
                                                                                                                                                 !1)
      IL_00c8:  ldloc.1
      IL_00c9:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00ce:  brtrue     IL_004f

      IL_00d3:  leave.s    IL_00df

    }  // end .try
    finally
    {
      IL_00d5:  ldloc.1
      IL_00d6:  brfalse.s  IL_00de

      IL_00d8:  ldloc.1
      IL_00d9:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00de:  endfinally
    }  // end handler
    IL_00df:  ret
  } // end of method Info::LoadAnimeCategoryInfo

  .method private hidebysig instance class [mscorlib]System.Collections.IEnumerator 
          LoadAnimeLoadInfoCoroutine(string _bundlePath,
                                     string _regex,
                                     class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> _dic,
                                     class Studio.Info/LoadAnimeInfoCoroutineFunc _func) cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.IteratorStateMachineAttribute::.ctor(class [mscorlib]System.Type) = ( 01 00 2D 53 74 75 64 69 6F 2E 49 6E 66 6F 2B 3C   // ..-Studio.Info+<
                                                                                                                                          4C 6F 61 64 41 6E 69 6D 65 4C 6F 61 64 49 6E 66   // LoadAnimeLoadInf
                                                                                                                                          6F 43 6F 72 6F 75 74 69 6E 65 3E 64 5F 5F 38 38   // oCoroutine>d__88
                                                                                                                                          00 00 ) 
    // 代码大小       43 (0x2b)
    .maxstack  8
    IL_0000:  ldc.i4.0
    IL_0001:  newobj     instance void Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::.ctor(int32)
    IL_0006:  dup
    IL_0007:  ldarg.0
    IL_0008:  stfld      class Studio.Info Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::'<>4__this'
    IL_000d:  dup
    IL_000e:  ldarg.1
    IL_000f:  stfld      string Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::_bundlePath
    IL_0014:  dup
    IL_0015:  ldarg.2
    IL_0016:  stfld      string Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::_regex
    IL_001b:  dup
    IL_001c:  ldarg.3
    IL_001d:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::_dic
    IL_0022:  dup
    IL_0023:  ldarg.s    _func
    IL_0025:  stfld      class Studio.Info/LoadAnimeInfoCoroutineFunc Studio.Info/'<LoadAnimeLoadInfoCoroutine>d__88'::_func
    IL_002a:  ret
  } // end of method Info::LoadAnimeLoadInfoCoroutine

  .method private hidebysig instance void 
          LoadAnimeLoadInfo(class [IL]ExcelData _ed,
                            class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> _dic) cil managed
  {
    // 代码大小       440 (0x1b8)
    .maxstack  8
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             int32 V_3,
             int32 V_4,
             int32 V_5,
             int32 V_6)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.2
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__89_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadAnimeLoadInfo>b__89_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__89_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br         IL_01a0

      IL_0045:  ldloc.0
      IL_0046:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_004b:  stloc.1
      IL_004c:  ldarg.0
      IL_004d:  ldfld      class Studio.Info/FileCheck Studio.Info::fileCheck
      IL_0052:  ldloc.1
      IL_0053:  ldc.i4.5
      IL_0054:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0059:  callvirt   instance bool Studio.Info/FileCheck::Check(string)
      IL_005e:  brfalse    IL_01a0

      IL_0063:  ldc.i4.0
      IL_0064:  stloc.2
      IL_0065:  ldc.i4.0
      IL_0066:  stloc.3
      IL_0067:  ldloc.1
      IL_0068:  ldloc.2
      IL_0069:  dup
      IL_006a:  ldc.i4.1
      IL_006b:  add
      IL_006c:  stloc.2
      IL_006d:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0072:  ldloca.s   V_3
      IL_0074:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0079:  brfalse    IL_01a0

      IL_007e:  ldc.i4.m1
      IL_007f:  stloc.s    V_4
      IL_0081:  ldloc.1
      IL_0082:  ldloc.2
      IL_0083:  dup
      IL_0084:  ldc.i4.1
      IL_0085:  add
      IL_0086:  stloc.2
      IL_0087:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_008c:  ldloca.s   V_4
      IL_008e:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0093:  brfalse    IL_01a0

      IL_0098:  ldloc.1
      IL_0099:  ldloc.2
      IL_009a:  dup
      IL_009b:  ldc.i4.1
      IL_009c:  add
      IL_009d:  stloc.2
      IL_009e:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_00a3:  call       int32 [mscorlib]System.Int32::Parse(string)
      IL_00a8:  stloc.s    V_5
      IL_00aa:  ldloc.1
      IL_00ab:  ldloc.2
      IL_00ac:  dup
      IL_00ad:  ldc.i4.1
      IL_00ae:  add
      IL_00af:  stloc.2
      IL_00b0:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_00b5:  call       int32 [mscorlib]System.Int32::Parse(string)
      IL_00ba:  stloc.s    V_6
      IL_00bc:  ldloc.s    V_5
      IL_00be:  brtrue.s   IL_00ec

      IL_00c0:  ldloc.s    V_6
      IL_00c2:  brtrue.s   IL_00d5

      IL_00c4:  ldloc.s    V_4
      IL_00c6:  brfalse.s  IL_00ec

      IL_00c8:  ldarg.0
      IL_00c9:  call       instance bool Studio.Info::get_IsInstallAI()
      IL_00ce:  brtrue.s   IL_00ec

      IL_00d0:  br         IL_01a0

      IL_00d5:  ldc.i4.1
      IL_00d6:  ldloc.s    V_6
      IL_00d8:  ldc.i4.s   12
      IL_00da:  call       bool [IL]MathfEx::RangeEqualOn<int32>(!!0,
                                                                 !!0,
                                                                 !!0)
      IL_00df:  brfalse.s  IL_00ec

      IL_00e1:  ldarg.0
      IL_00e2:  call       instance bool Studio.Info::get_IsInstallAI()
      IL_00e7:  brfalse    IL_01a0

      IL_00ec:  ldarg.2
      IL_00ed:  ldloc.s    V_5
      IL_00ef:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::ContainsKey(!0)
      IL_00f4:  brtrue.s   IL_0103

      IL_00f6:  ldarg.2
      IL_00f7:  ldloc.s    V_5
      IL_00f9:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>::.ctor()
      IL_00fe:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::Add(!0,
                                                                                                                                                                                                                                                                           !1)
      IL_0103:  ldarg.2
      IL_0104:  ldloc.s    V_5
      IL_0106:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::get_Item(!0)
      IL_010b:  ldloc.s    V_6
      IL_010d:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>::ContainsKey(!0)
      IL_0112:  brtrue.s   IL_0128

      IL_0114:  ldarg.2
      IL_0115:  ldloc.s    V_5
      IL_0117:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::get_Item(!0)
      IL_011c:  ldloc.s    V_6
      IL_011e:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>::.ctor()
      IL_0123:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>::Add(!0,
                                                                                                                                                                                                            !1)
      IL_0128:  ldarg.2
      IL_0129:  ldloc.s    V_5
      IL_012b:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::get_Item(!0)
      IL_0130:  ldloc.s    V_6
      IL_0132:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>::get_Item(!0)
      IL_0137:  ldloc.s    V_4
      IL_0139:  newobj     instance void Studio.Info/AnimeLoadInfo::.ctor()
      IL_013e:  dup
      IL_013f:  ldloc.3
      IL_0140:  stfld      int32 Studio.Info/AnimeLoadInfo::sort
      IL_0145:  dup
      IL_0146:  ldloc.1
      IL_0147:  ldloc.2
      IL_0148:  dup
      IL_0149:  ldc.i4.1
      IL_014a:  add
      IL_014b:  stloc.2
      IL_014c:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0151:  stfld      string Studio.Info/LoadCommonInfo::name
      IL_0156:  dup
      IL_0157:  ldloc.1
      IL_0158:  ldloc.2
      IL_0159:  dup
      IL_015a:  ldc.i4.1
      IL_015b:  add
      IL_015c:  stloc.2
      IL_015d:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0162:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_0167:  dup
      IL_0168:  ldloc.1
      IL_0169:  ldloc.2
      IL_016a:  dup
      IL_016b:  ldc.i4.1
      IL_016c:  add
      IL_016d:  stloc.2
      IL_016e:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0173:  stfld      string Studio.Info/FileInfo::fileName
      IL_0178:  dup
      IL_0179:  ldloc.1
      IL_017a:  ldloc.2
      IL_017b:  dup
      IL_017c:  ldc.i4.1
      IL_017d:  add
      IL_017e:  stloc.2
      IL_017f:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0184:  stfld      string Studio.Info/AnimeLoadInfo::clip
      IL_0189:  dup
      IL_018a:  ldloc.1
      IL_018b:  ldloc.2
      IL_018c:  dup
      IL_018d:  ldc.i4.1
      IL_018e:  add
      IL_018f:  stloc.2
      IL_0190:  ldc.i4.1
      IL_0191:  call       class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/OptionItemInfo> Studio.Info/AnimeLoadInfo::LoadOption(class [mscorlib]System.Collections.Generic.List`1<string>,
                                                                                                                                                     int32,
                                                                                                                                                     bool)
      IL_0196:  stfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.Info/OptionItemInfo> Studio.Info/AnimeLoadInfo::option
      IL_019b:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>::set_Item(!0,
                                                                                                                                                  !1)
      IL_01a0:  ldloc.0
      IL_01a1:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_01a6:  brtrue     IL_0045

      IL_01ab:  leave.s    IL_01b7

    }  // end .try
    finally
    {
      IL_01ad:  ldloc.0
      IL_01ae:  brfalse.s  IL_01b6

      IL_01b0:  ldloc.0
      IL_01b1:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_01b6:  endfinally
    }  // end handler
    IL_01b7:  ret
  } // end of method Info::LoadAnimeLoadInfo

  .method private hidebysig instance void 
          LoadHAnimeLoadInfo(class [IL]ExcelData _ed,
                             class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> _dic) cil managed
  {
    // 代码大小       278 (0x116)
    .maxstack  4
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             int32 V_3,
             int32 V_4,
             int32 V_5)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.2
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__90_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadHAnimeLoadInfo>b__90_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__90_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br         IL_00fe

      IL_0045:  ldloc.0
      IL_0046:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_004b:  stloc.1
      IL_004c:  ldarg.0
      IL_004d:  ldfld      class Studio.Info/FileCheck Studio.Info::fileCheck
      IL_0052:  ldloc.1
      IL_0053:  ldc.i4.5
      IL_0054:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0059:  callvirt   instance bool Studio.Info/FileCheck::Check(string)
      IL_005e:  brfalse    IL_00fe

      IL_0063:  ldc.i4.0
      IL_0064:  stloc.2
      IL_0065:  ldloc.1
      IL_0066:  ldc.i4.0
      IL_0067:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_006c:  ldloca.s   V_2
      IL_006e:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0073:  brfalse    IL_00fe

      IL_0078:  ldc.i4.0
      IL_0079:  stloc.3
      IL_007a:  ldloc.1
      IL_007b:  ldc.i4.1
      IL_007c:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0081:  ldloca.s   V_3
      IL_0083:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_0088:  brfalse.s  IL_00fe

      IL_008a:  ldloc.1
      IL_008b:  ldc.i4.2
      IL_008c:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_0091:  call       int32 [mscorlib]System.Int32::Parse(string)
      IL_0096:  stloc.s    V_4
      IL_0098:  ldloc.1
      IL_0099:  ldc.i4.3
      IL_009a:  call       !!0 [IL]NullCheck::SafeGet<string>(class [mscorlib]System.Collections.Generic.IReadOnlyList`1<!!0>,
                                                              int32)
      IL_009f:  call       int32 [mscorlib]System.Int32::Parse(string)
      IL_00a4:  stloc.s    V_5
      IL_00a6:  ldarg.2
      IL_00a7:  ldloc.s    V_4
      IL_00a9:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::ContainsKey(!0)
      IL_00ae:  brtrue.s   IL_00bd

      IL_00b0:  ldarg.2
      IL_00b1:  ldloc.s    V_4
      IL_00b3:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>::.ctor()
      IL_00b8:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::Add(!0,
                                                                                                                                                                                                                                                                           !1)
      IL_00bd:  ldarg.2
      IL_00be:  ldloc.s    V_4
      IL_00c0:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::get_Item(!0)
      IL_00c5:  ldloc.s    V_5
      IL_00c7:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>::ContainsKey(!0)
      IL_00cc:  brtrue.s   IL_00e2

      IL_00ce:  ldarg.2
      IL_00cf:  ldloc.s    V_4
      IL_00d1:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::get_Item(!0)
      IL_00d6:  ldloc.s    V_5
      IL_00d8:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>::.ctor()
      IL_00dd:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>::Add(!0,
                                                                                                                                                                                                            !1)
      IL_00e2:  ldarg.2
      IL_00e3:  ldloc.s    V_4
      IL_00e5:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::get_Item(!0)
      IL_00ea:  ldloc.s    V_5
      IL_00ec:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>::get_Item(!0)
      IL_00f1:  ldloc.3
      IL_00f2:  ldc.i4.4
      IL_00f3:  ldloc.1
      IL_00f4:  newobj     instance void Studio.Info/HAnimeLoadInfo::.ctor(int32,
                                                                           class [mscorlib]System.Collections.Generic.List`1<string>)
      IL_00f9:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>::set_Item(!0,
                                                                                                                                                  !1)
      IL_00fe:  ldloc.0
      IL_00ff:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_0104:  brtrue     IL_0045

      IL_0109:  leave.s    IL_0115

    }  // end .try
    finally
    {
      IL_010b:  ldloc.0
      IL_010c:  brfalse.s  IL_0114

      IL_010e:  ldloc.0
      IL_010f:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0114:  endfinally
    }  // end handler
    IL_0115:  ret
  } // end of method Info::LoadHAnimeLoadInfo

  .method private hidebysig instance class [mscorlib]System.Collections.IEnumerator 
          LoadVoiceLoadInfoCoroutine(string _bundlePath,
                                     string _regex) cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.IteratorStateMachineAttribute::.ctor(class [mscorlib]System.Type) = ( 01 00 2D 53 74 75 64 69 6F 2E 49 6E 66 6F 2B 3C   // ..-Studio.Info+<
                                                                                                                                          4C 6F 61 64 56 6F 69 63 65 4C 6F 61 64 49 6E 66   // LoadVoiceLoadInf
                                                                                                                                          6F 43 6F 72 6F 75 74 69 6E 65 3E 64 5F 5F 39 31   // oCoroutine>d__91
                                                                                                                                          00 00 ) 
    // 代码大小       28 (0x1c)
    .maxstack  8
    IL_0000:  ldc.i4.0
    IL_0001:  newobj     instance void Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::.ctor(int32)
    IL_0006:  dup
    IL_0007:  ldarg.0
    IL_0008:  stfld      class Studio.Info Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::'<>4__this'
    IL_000d:  dup
    IL_000e:  ldarg.1
    IL_000f:  stfld      string Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::_bundlePath
    IL_0014:  dup
    IL_0015:  ldarg.2
    IL_0016:  stfld      string Studio.Info/'<LoadVoiceLoadInfoCoroutine>d__91'::_regex
    IL_001b:  ret
  } // end of method Info::LoadVoiceLoadInfoCoroutine

  .method private hidebysig instance void 
          LoadVoiceLoadInfo(class [IL]ExcelData _ed) cil managed
  {
    // 代码大小       92 (0x5c)
    .maxstack  3
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1)
    IL_0000:  ldarg.1
    IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0006:  ldc.i4.2
    IL_0007:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_000c:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__92_0'
    IL_0011:  dup
    IL_0012:  brtrue.s   IL_002b

    IL_0014:  pop
    IL_0015:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_001a:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadVoiceLoadInfo>b__92_0'(class [IL]ExcelData/Param)
    IL_0020:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_0025:  dup
    IL_0026:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__92_0'
    IL_002b:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_0030:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_0035:  stloc.0
    .try
    {
      IL_0036:  br.s       IL_0047

      IL_0038:  ldloc.0
      IL_0039:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_003e:  stloc.1
      IL_003f:  ldarg.0
      IL_0040:  ldloc.1
      IL_0041:  call       instance class Studio.Info/LoadCommonInfo Studio.Info::LoadVoiceLoadInfo(class [mscorlib]System.Collections.Generic.List`1<string>)
      IL_0046:  pop
      IL_0047:  ldloc.0
      IL_0048:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_004d:  brtrue.s   IL_0038

      IL_004f:  leave.s    IL_005b

    }  // end .try
    finally
    {
      IL_0051:  ldloc.0
      IL_0052:  brfalse.s  IL_005a

      IL_0054:  ldloc.0
      IL_0055:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_005a:  endfinally
    }  // end handler
    IL_005b:  ret
  } // end of method Info::LoadVoiceLoadInfo

  .method private hidebysig instance class Studio.Info/LoadCommonInfo 
          LoadVoiceLoadInfo(class [mscorlib]System.Collections.Generic.List`1<string> _list) cil managed
  {
    // 代码大小       236 (0xec)
    .maxstack  5
    .locals init (int32 V_0,
             class Studio.Info/LoadCommonInfo V_1,
             int32 V_2,
             int32 V_3,
             int32 V_4)
    IL_0000:  ldc.i4.0
    IL_0001:  stloc.0
    IL_0002:  newobj     instance void Studio.Info/LoadCommonInfo::.ctor()
    IL_0007:  stloc.1
    IL_0008:  ldc.i4.m1
    IL_0009:  stloc.2
    IL_000a:  ldarg.1
    IL_000b:  ldloc.0
    IL_000c:  dup
    IL_000d:  ldc.i4.1
    IL_000e:  add
    IL_000f:  stloc.0
    IL_0010:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
    IL_0015:  ldloca.s   V_2
    IL_0017:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                               int32&)
    IL_001c:  brtrue.s   IL_0020

    IL_001e:  ldnull
    IL_001f:  ret

    IL_0020:  ldc.i4.m1
    IL_0021:  stloc.3
    IL_0022:  ldarg.1
    IL_0023:  ldloc.0
    IL_0024:  dup
    IL_0025:  ldc.i4.1
    IL_0026:  add
    IL_0027:  stloc.0
    IL_0028:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
    IL_002d:  ldloca.s   V_3
    IL_002f:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                               int32&)
    IL_0034:  brtrue.s   IL_0038

    IL_0036:  ldnull
    IL_0037:  ret

    IL_0038:  ldc.i4.m1
    IL_0039:  stloc.s    V_4
    IL_003b:  ldarg.1
    IL_003c:  ldloc.0
    IL_003d:  dup
    IL_003e:  ldc.i4.1
    IL_003f:  add
    IL_0040:  stloc.0
    IL_0041:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
    IL_0046:  ldloca.s   V_4
    IL_0048:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                               int32&)
    IL_004d:  brtrue.s   IL_0051

    IL_004f:  ldnull
    IL_0050:  ret

    IL_0051:  ldloc.1
    IL_0052:  ldarg.1
    IL_0053:  ldloc.0
    IL_0054:  dup
    IL_0055:  ldc.i4.1
    IL_0056:  add
    IL_0057:  stloc.0
    IL_0058:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
    IL_005d:  stfld      string Studio.Info/LoadCommonInfo::name
    IL_0062:  ldloc.1
    IL_0063:  ldarg.1
    IL_0064:  ldloc.0
    IL_0065:  dup
    IL_0066:  ldc.i4.1
    IL_0067:  add
    IL_0068:  stloc.0
    IL_0069:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
    IL_006e:  stfld      string Studio.Info/FileInfo::bundlePath
    IL_0073:  ldloc.1
    IL_0074:  ldarg.1
    IL_0075:  ldloc.0
    IL_0076:  dup
    IL_0077:  ldc.i4.1
    IL_0078:  add
    IL_0079:  stloc.0
    IL_007a:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
    IL_007f:  stfld      string Studio.Info/FileInfo::fileName
    IL_0084:  ldarg.0
    IL_0085:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>> Studio.Info::dicVoiceLoadInfo
    IL_008a:  ldloc.3
    IL_008b:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>>::ContainsKey(!0)
    IL_0090:  brtrue.s   IL_00a3

    IL_0092:  ldarg.0
    IL_0093:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>> Studio.Info::dicVoiceLoadInfo
    IL_0098:  ldloc.3
    IL_0099:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>::.ctor()
    IL_009e:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>>::Add(!0,
                                                                                                                                                                                                                                                                          !1)
    IL_00a3:  ldarg.0
    IL_00a4:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>> Studio.Info::dicVoiceLoadInfo
    IL_00a9:  ldloc.3
    IL_00aa:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>>::get_Item(!0)
    IL_00af:  ldloc.s    V_4
    IL_00b1:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>::ContainsKey(!0)
    IL_00b6:  brtrue.s   IL_00d0

    IL_00b8:  ldarg.0
    IL_00b9:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>> Studio.Info::dicVoiceLoadInfo
    IL_00be:  ldloc.3
    IL_00bf:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>>::get_Item(!0)
    IL_00c4:  ldloc.s    V_4
    IL_00c6:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>::.ctor()
    IL_00cb:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>::Add(!0,
                                                                                                                                                                                                           !1)
    IL_00d0:  ldarg.0
    IL_00d1:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>> Studio.Info::dicVoiceLoadInfo
    IL_00d6:  ldloc.3
    IL_00d7:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>>::get_Item(!0)
    IL_00dc:  ldloc.s    V_4
    IL_00de:  callvirt   instance !1 class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>::get_Item(!0)
    IL_00e3:  ldloc.2
    IL_00e4:  ldloc.1
    IL_00e5:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>::set_Item(!0,
                                                                                                                                                 !1)
    IL_00ea:  ldloc.1
    IL_00eb:  ret
  } // end of method Info::LoadVoiceLoadInfo

  .method private hidebysig instance void 
          LoadSoundLoadInfo(class [IL]ExcelData _ed,
                            class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> _dic) cil managed
  {
    // 代码大小       181 (0xb5)
    .maxstack  8
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             int32 V_3)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.1
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__94_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadSoundLoadInfo>b__94_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__94_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br.s       IL_00a0

      IL_0042:  ldloc.0
      IL_0043:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_0048:  stloc.1
      IL_0049:  ldc.i4.0
      IL_004a:  stloc.2
      IL_004b:  ldc.i4.m1
      IL_004c:  stloc.3
      IL_004d:  ldloc.1
      IL_004e:  ldloc.2
      IL_004f:  dup
      IL_0050:  ldc.i4.1
      IL_0051:  add
      IL_0052:  stloc.2
      IL_0053:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0058:  ldloca.s   V_3
      IL_005a:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_005f:  brfalse.s  IL_00a0

      IL_0061:  ldarg.2
      IL_0062:  ldloc.3
      IL_0063:  newobj     instance void Studio.Info/LoadCommonInfo::.ctor()
      IL_0068:  dup
      IL_0069:  ldloc.1
      IL_006a:  ldloc.2
      IL_006b:  dup
      IL_006c:  ldc.i4.1
      IL_006d:  add
      IL_006e:  stloc.2
      IL_006f:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0074:  stfld      string Studio.Info/LoadCommonInfo::name
      IL_0079:  dup
      IL_007a:  ldloc.1
      IL_007b:  ldloc.2
      IL_007c:  dup
      IL_007d:  ldc.i4.1
      IL_007e:  add
      IL_007f:  stloc.2
      IL_0080:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0085:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_008a:  dup
      IL_008b:  ldloc.1
      IL_008c:  ldloc.2
      IL_008d:  dup
      IL_008e:  ldc.i4.1
      IL_008f:  add
      IL_0090:  stloc.2
      IL_0091:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0096:  stfld      string Studio.Info/FileInfo::fileName
      IL_009b:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>::set_Item(!0,
                                                                                                                                                   !1)
      IL_00a0:  ldloc.0
      IL_00a1:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00a6:  brtrue.s   IL_0042

      IL_00a8:  leave.s    IL_00b4

    }  // end .try
    finally
    {
      IL_00aa:  ldloc.0
      IL_00ab:  brfalse.s  IL_00b3

      IL_00ad:  ldloc.0
      IL_00ae:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00b3:  endfinally
    }  // end handler
    IL_00b4:  ret
  } // end of method Info::LoadSoundLoadInfo

  .method private hidebysig instance void 
          LoadBGMLoadInfo(class [IL]ExcelData _ed) cil managed
  {
    // 代码大小       199 (0xc7)
    .maxstack  8
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             int32 V_3)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.1
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__95_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadBGMLoadInfo>b__95_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__95_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br.s       IL_00b2

      IL_0042:  ldloc.0
      IL_0043:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_0048:  stloc.1
      IL_0049:  ldc.i4.0
      IL_004a:  stloc.2
      IL_004b:  ldc.i4.m1
      IL_004c:  stloc.3
      IL_004d:  ldloc.1
      IL_004e:  ldloc.2
      IL_004f:  dup
      IL_0050:  ldc.i4.1
      IL_0051:  add
      IL_0052:  stloc.2
      IL_0053:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0058:  ldloca.s   V_3
      IL_005a:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_005f:  brfalse.s  IL_00b2

      IL_0061:  ldloc.3
      IL_0062:  ldc.i4.s   100
      IL_0064:  bge.s      IL_006e

      IL_0066:  ldarg.0
      IL_0067:  call       instance bool Studio.Info::get_IsInstallAI()
      IL_006c:  brfalse.s  IL_00b2

      IL_006e:  ldarg.0
      IL_006f:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> Studio.Info::dicBGMLoadInfo
      IL_0074:  ldloc.3
      IL_0075:  newobj     instance void Studio.Info/LoadCommonInfo::.ctor()
      IL_007a:  dup
      IL_007b:  ldloc.1
      IL_007c:  ldloc.2
      IL_007d:  dup
      IL_007e:  ldc.i4.1
      IL_007f:  add
      IL_0080:  stloc.2
      IL_0081:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0086:  stfld      string Studio.Info/LoadCommonInfo::name
      IL_008b:  dup
      IL_008c:  ldloc.1
      IL_008d:  ldloc.2
      IL_008e:  dup
      IL_008f:  ldc.i4.1
      IL_0090:  add
      IL_0091:  stloc.2
      IL_0092:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0097:  stfld      string Studio.Info/FileInfo::bundlePath
      IL_009c:  dup
      IL_009d:  ldloc.1
      IL_009e:  ldloc.2
      IL_009f:  dup
      IL_00a0:  ldc.i4.1
      IL_00a1:  add
      IL_00a2:  stloc.2
      IL_00a3:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_00a8:  stfld      string Studio.Info/FileInfo::fileName
      IL_00ad:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>::set_Item(!0,
                                                                                                                                                   !1)
      IL_00b2:  ldloc.0
      IL_00b3:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00b8:  brtrue.s   IL_0042

      IL_00ba:  leave.s    IL_00c6

    }  // end .try
    finally
    {
      IL_00bc:  ldloc.0
      IL_00bd:  brfalse.s  IL_00c5

      IL_00bf:  ldloc.0
      IL_00c0:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00c5:  endfinally
    }  // end handler
    IL_00c6:  ret
  } // end of method Info::LoadBGMLoadInfo

  .method private hidebysig instance void 
          LoadMapLoadInfo(class [IL]ExcelData _ed) cil managed
  {
    // 代码大小       148 (0x94)
    .maxstack  4
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             int32 V_3)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.2
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__96_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadMapLoadInfo>b__96_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__96_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br.s       IL_007f

      IL_0042:  ldloc.0
      IL_0043:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_0048:  stloc.1
      IL_0049:  ldc.i4.0
      IL_004a:  stloc.2
      IL_004b:  ldc.i4.m1
      IL_004c:  stloc.3
      IL_004d:  ldloc.1
      IL_004e:  ldloc.2
      IL_004f:  dup
      IL_0050:  ldc.i4.1
      IL_0051:  add
      IL_0052:  stloc.2
      IL_0053:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0058:  ldloca.s   V_3
      IL_005a:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_005f:  brfalse.s  IL_007f

      IL_0061:  ldloc.3
      IL_0062:  ldc.i4.1
      IL_0063:  bgt.un.s   IL_006d

      IL_0065:  ldarg.0
      IL_0066:  call       instance bool Studio.Info::get_IsInstallAI()
      IL_006b:  brfalse.s  IL_007f

      IL_006d:  ldarg.0
      IL_006e:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/MapLoadInfo> Studio.Info::dicMapLoadInfo
      IL_0073:  ldloc.3
      IL_0074:  ldloc.1
      IL_0075:  newobj     instance void Studio.Info/MapLoadInfo::.ctor(class [mscorlib]System.Collections.Generic.List`1<string>)
      IL_007a:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/MapLoadInfo>::set_Item(!0,
                                                                                                                                                !1)
      IL_007f:  ldloc.0
      IL_0080:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_0085:  brtrue.s   IL_0042

      IL_0087:  leave.s    IL_0093

    }  // end .try
    finally
    {
      IL_0089:  ldloc.0
      IL_008a:  brfalse.s  IL_0092

      IL_008c:  ldloc.0
      IL_008d:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0092:  endfinally
    }  // end handler
    IL_0093:  ret
  } // end of method Info::LoadMapLoadInfo

  .method private hidebysig instance void 
          LoadSkyPatternInfo(class [IL]ExcelData _ed) cil managed
  {
    // 代码大小       136 (0x88)
    .maxstack  4
    .locals init (class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>> V_0,
             class [mscorlib]System.Collections.Generic.List`1<string> V_1,
             int32 V_2,
             int32 V_3)
    IL_0000:  ldarg.1
    IL_0001:  ldnull
    IL_0002:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0007:  brfalse.s  IL_000a

    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class [IL]ExcelData/Param> [IL]ExcelData::list
    IL_0010:  ldc.i4.2
    IL_0011:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Skip<class [IL]ExcelData/Param>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                            int32)
    IL_0016:  ldsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__97_0'
    IL_001b:  dup
    IL_001c:  brtrue.s   IL_0035

    IL_001e:  pop
    IL_001f:  ldsfld     class Studio.Info/'<>c' Studio.Info/'<>c'::'<>9'
    IL_0024:  ldftn      instance class [mscorlib]System.Collections.Generic.List`1<string> Studio.Info/'<>c'::'<LoadSkyPatternInfo>b__97_0'(class [IL]ExcelData/Param)
    IL_002a:  newobj     instance void class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>::.ctor(object,
                                                                                                                                                                 native int)
    IL_002f:  dup
    IL_0030:  stsfld     class [mscorlib]System.Func`2<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>> Studio.Info/'<>c'::'<>9__97_0'
    IL_0035:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!1> [System.Core]System.Linq.Enumerable::Select<class [IL]ExcelData/Param,class [mscorlib]System.Collections.Generic.List`1<string>>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                                                                        class [mscorlib]System.Func`2<!!0,!!1>)
    IL_003a:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class [mscorlib]System.Collections.Generic.List`1<string>>::GetEnumerator()
    IL_003f:  stloc.0
    .try
    {
      IL_0040:  br.s       IL_0073

      IL_0042:  ldloc.0
      IL_0043:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class [mscorlib]System.Collections.Generic.List`1<string>>::get_Current()
      IL_0048:  stloc.1
      IL_0049:  ldc.i4.0
      IL_004a:  stloc.2
      IL_004b:  ldc.i4.m1
      IL_004c:  stloc.3
      IL_004d:  ldloc.1
      IL_004e:  ldloc.2
      IL_004f:  dup
      IL_0050:  ldc.i4.1
      IL_0051:  add
      IL_0052:  stloc.2
      IL_0053:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<string>::get_Item(int32)
      IL_0058:  ldloca.s   V_3
      IL_005a:  call       bool [mscorlib]System.Int32::TryParse(string,
                                                                 int32&)
      IL_005f:  brfalse.s  IL_0073

      IL_0061:  ldarg.0
      IL_0062:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/SkyPatternInfo> Studio.Info::dicSkyPatternInfo
      IL_0067:  ldloc.3
      IL_0068:  ldloc.1
      IL_0069:  newobj     instance void Studio.Info/SkyPatternInfo::.ctor(class [mscorlib]System.Collections.Generic.List`1<string>)
      IL_006e:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/SkyPatternInfo>::set_Item(!0,
                                                                                                                                                   !1)
      IL_0073:  ldloc.0
      IL_0074:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_0079:  brtrue.s   IL_0042

      IL_007b:  leave.s    IL_0087

    }  // end .try
    finally
    {
      IL_007d:  ldloc.0
      IL_007e:  brfalse.s  IL_0086

      IL_0080:  ldloc.0
      IL_0081:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0086:  endfinally
    }  // end handler
    IL_0087:  ret
  } // end of method Info::LoadSkyPatternInfo

  .method family hidebysig virtual instance void 
          Awake() cil managed
  {
    // 代码大小       40 (0x28)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  call       instance bool class [IL]Singleton`1<class Studio.Info>::CheckInstance()
    IL_0006:  brtrue.s   IL_0009

    IL_0008:  ret

    IL_0009:  ldarg.0
    IL_000a:  call       instance class [UnityEngine.CoreModule]UnityEngine.GameObject [UnityEngine.CoreModule]UnityEngine.Component::get_gameObject()
    IL_000f:  call       void [UnityEngine.CoreModule]UnityEngine.Object::DontDestroyOnLoad(class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0014:  ldarg.0
    IL_0015:  call       instance void Studio.Info::CheckIsAI()
    IL_001a:  ldarg.0
    IL_001b:  call       instance void Studio.Info::CheckIsAdd()
    IL_0020:  ldarg.0
    IL_0021:  ldc.i4.0
    IL_0022:  call       instance void Studio.Info::set_isLoadList(bool)
    IL_0027:  ret
  } // end of method Info::Awake

  .method public hidebysig specialname rtspecialname 
          instance void  .ctor() cil managed
  {
    // 代码大小       183 (0xb7)
    .maxstack  2
    IL_0000:  ldarg.0
    IL_0001:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/BoneInfo>::.ctor()
    IL_0006:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/BoneInfo> Studio.Info::dicBoneInfo
    IL_000b:  ldarg.0
    IL_000c:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::.ctor()
    IL_0011:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicItemGroupCategory
    IL_0016:  ldarg.0
    IL_0017:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>>::.ctor()
    IL_001c:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/ItemLoadInfo>>> Studio.Info::dicItemLoadInfo
    IL_0021:  ldarg.0
    IL_0022:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>>::.ctor()
    IL_0027:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.ItemColorData/ColorData>>> Studio.Info::dicItemColorData
    IL_002c:  ldarg.0
    IL_002d:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AccessoryGroupInfo>::.ctor()
    IL_0032:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AccessoryGroupInfo> Studio.Info::dicAccessoryGroup
    IL_0037:  ldarg.0
    IL_0038:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LightLoadInfo>::.ctor()
    IL_003d:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LightLoadInfo> Studio.Info::dicLightLoadInfo
    IL_0042:  ldarg.0
    IL_0043:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::.ctor()
    IL_0048:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicAGroupCategory
    IL_004d:  ldarg.0
    IL_004e:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>>::.ctor()
    IL_0053:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/AnimeLoadInfo>>> Studio.Info::dicAnimeLoadInfo
    IL_0058:  ldarg.0
    IL_0059:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo>::.ctor()
    IL_005e:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/GroupInfo> Studio.Info::dicVoiceGroupCategory
    IL_0063:  ldarg.0
    IL_0064:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>>::.ctor()
    IL_0069:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>>> Studio.Info::dicVoiceLoadInfo
    IL_006e:  ldarg.0
    IL_006f:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>::.ctor()
    IL_0074:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> Studio.Info::dicBGMLoadInfo
    IL_0079:  ldarg.0
    IL_007a:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>::.ctor()
    IL_007f:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> Studio.Info::dicENVLoadInfo
    IL_0084:  ldarg.0
    IL_0085:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/MapLoadInfo>::.ctor()
    IL_008a:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/MapLoadInfo> Studio.Info::dicMapLoadInfo
    IL_008f:  ldarg.0
    IL_0090:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>::.ctor()
    IL_0095:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> Studio.Info::dicColorGradingLoadInfo
    IL_009a:  ldarg.0
    IL_009b:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo>::.ctor()
    IL_00a0:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/LoadCommonInfo> Studio.Info::dicReflectionProbeLoadInfo
    IL_00a5:  ldarg.0
    IL_00a6:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/SkyPatternInfo>::.ctor()
    IL_00ab:  stfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/SkyPatternInfo> Studio.Info::dicSkyPatternInfo
    IL_00b0:  ldarg.0
    IL_00b1:  call       instance void class [IL]Singleton`1<class Studio.Info>::.ctor()
    IL_00b6:  ret
  } // end of method Info::.ctor

  .property instance int32 AccessoryPointNum()
  {
    .get instance int32 Studio.Info::get_AccessoryPointNum()
    .set instance void Studio.Info::set_AccessoryPointNum(int32)
  } // end of property Info::AccessoryPointNum
  .property instance int32[] AccessoryPointsIndex()
  {
    .get instance int32[] Studio.Info::get_AccessoryPointsIndex()
  } // end of property Info::AccessoryPointsIndex
  .property instance class [IL]ExcelData accessoryPointGroup()
  {
    .get instance class [IL]ExcelData Studio.Info::get_accessoryPointGroup()
  } // end of property Info::accessoryPointGroup
  .property instance bool isLoadList()
  {
    .get instance bool Studio.Info::get_isLoadList()
    .set instance void Studio.Info::set_isLoadList(bool)
  } // end of property Info::isLoadList
  .property instance bool IsInstallAI()
  {
    .get instance bool Studio.Info::get_IsInstallAI()
    .set instance void Studio.Info::set_IsInstallAI(bool)
  } // end of property Info::IsInstallAI
  .property instance bool IsInstallAdd()
  {
    .get instance bool Studio.Info::get_IsInstallAdd()
    .set instance void Studio.Info::set_IsInstallAdd(bool)
  } // end of property Info::IsInstallAdd
} // end of class Studio.Info

// *********** 反汇编完成 ***********************
// 警告: 创建了 Win32 资源文件 tmp/Assembly-CSharp-Info.res
