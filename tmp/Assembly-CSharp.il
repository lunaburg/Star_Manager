
//  Microsoft (R) .NET Framework IL Disassembler.  Version 4.8.3928.0



// 警告 : 这是一个不完整的反汇编程序，不适合于重新汇编



.class public auto ansi beforefieldinit Studio.FKCtrl
       extends [UnityEngine.CoreModule]UnityEngine.MonoBehaviour
{
  .class auto ansi nested private beforefieldinit TargetInfo
         extends [mscorlib]System.Object
  {
    .class auto ansi serializable sealed nested private beforefieldinit '<>c'
           extends [mscorlib]System.Object
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      .field public static initonly class Studio.FKCtrl/TargetInfo/'<>c' '<>9'
      .field public static class [mscorlib]System.Action`1<class Studio.OCIChar/SyncBoneInfo> '<>9__26_1'
      .method private hidebysig specialname rtspecialname static 
              void  .cctor() cil managed
      {
        // 代码大小       11 (0xb)
        .maxstack  8
        IL_0000:  newobj     instance void Studio.FKCtrl/TargetInfo/'<>c'::.ctor()
        IL_0005:  stsfld     class Studio.FKCtrl/TargetInfo/'<>c' Studio.FKCtrl/TargetInfo/'<>c'::'<>9'
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

      .method assembly hidebysig instance void 
              '<.ctor>b__26_1'(class Studio.OCIChar/SyncBoneInfo _sbi) cil managed
      {
        // 代码大小       12 (0xc)
        .maxstack  8
        IL_0000:  ldarg.1
        IL_0001:  call       valuetype [UnityEngine.CoreModule]UnityEngine.Quaternion [UnityEngine.CoreModule]UnityEngine.Quaternion::get_identity()
        IL_0006:  callvirt   instance void Studio.OCIChar/SyncBoneInfo::set_LocalRotation(valuetype [UnityEngine.CoreModule]UnityEngine.Quaternion)
        IL_000b:  ret
      } // end of method '<>c'::'<.ctor>b__26_1'

    } // end of class '<>c'

    .field public class [UnityEngine.CoreModule]UnityEngine.GameObject gameObject
    .field private class [UnityEngine.CoreModule]UnityEngine.Transform m_Transform
    .field public class Studio.ChangeAmount changeAmount
    .field private valuetype Studio.OIBoneInfo/BoneGroup '<group>k__BackingField'
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field private int32 '<level>k__BackingField'
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field private bool '<boneWeight>k__BackingField'
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field private int32 '<boneID>k__BackingField'
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field private class [UniRx]UniRx.BoolReactiveProperty _enable
    .field private class Studio.OCIChar/SyncBoneInfo syncBoneInfo
    .method public hidebysig specialname 
            instance class [UnityEngine.CoreModule]UnityEngine.Transform 
            get_transform() cil managed
    {
      // 代码大小       38 (0x26)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl/TargetInfo::m_Transform
      IL_0006:  ldnull
      IL_0007:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                        class [UnityEngine.CoreModule]UnityEngine.Object)
      IL_000c:  brfalse.s  IL_001f

      IL_000e:  ldarg.0
      IL_000f:  ldarg.0
      IL_0010:  ldfld      class [UnityEngine.CoreModule]UnityEngine.GameObject Studio.FKCtrl/TargetInfo::gameObject
      IL_0015:  callvirt   instance class [UnityEngine.CoreModule]UnityEngine.Transform [UnityEngine.CoreModule]UnityEngine.GameObject::get_transform()
      IL_001a:  stfld      class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl/TargetInfo::m_Transform
      IL_001f:  ldarg.0
      IL_0020:  ldfld      class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl/TargetInfo::m_Transform
      IL_0025:  ret
    } // end of method TargetInfo::get_transform

    .method public hidebysig specialname 
            instance valuetype Studio.OIBoneInfo/BoneGroup 
            get_group() cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/TargetInfo::'<group>k__BackingField'
      IL_0006:  ret
    } // end of method TargetInfo::get_group

    .method private hidebysig specialname 
            instance void  set_group(valuetype Studio.OIBoneInfo/BoneGroup 'value') cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       8 (0x8)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldarg.1
      IL_0002:  stfld      valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/TargetInfo::'<group>k__BackingField'
      IL_0007:  ret
    } // end of method TargetInfo::set_group

    .method public hidebysig specialname 
            instance int32  get_level() cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      int32 Studio.FKCtrl/TargetInfo::'<level>k__BackingField'
      IL_0006:  ret
    } // end of method TargetInfo::get_level

    .method private hidebysig specialname 
            instance void  set_level(int32 'value') cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       8 (0x8)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldarg.1
      IL_0002:  stfld      int32 Studio.FKCtrl/TargetInfo::'<level>k__BackingField'
      IL_0007:  ret
    } // end of method TargetInfo::set_level

    .method public hidebysig specialname 
            instance bool  get_boneWeight() cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      bool Studio.FKCtrl/TargetInfo::'<boneWeight>k__BackingField'
      IL_0006:  ret
    } // end of method TargetInfo::get_boneWeight

    .method public hidebysig specialname 
            instance void  set_boneWeight(bool 'value') cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       8 (0x8)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldarg.1
      IL_0002:  stfld      bool Studio.FKCtrl/TargetInfo::'<boneWeight>k__BackingField'
      IL_0007:  ret
    } // end of method TargetInfo::set_boneWeight

    .method public hidebysig specialname 
            instance int32  get_boneID() cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      int32 Studio.FKCtrl/TargetInfo::'<boneID>k__BackingField'
      IL_0006:  ret
    } // end of method TargetInfo::get_boneID

    .method private hidebysig specialname 
            instance void  set_boneID(int32 'value') cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       8 (0x8)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldarg.1
      IL_0002:  stfld      int32 Studio.FKCtrl/TargetInfo::'<boneID>k__BackingField'
      IL_0007:  ret
    } // end of method TargetInfo::set_boneID

    .method public hidebysig specialname 
            instance bool  get_enable() cil managed
    {
      // 代码大小       12 (0xc)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      class [UniRx]UniRx.BoolReactiveProperty Studio.FKCtrl/TargetInfo::_enable
      IL_0006:  callvirt   instance !0 class [UniRx]UniRx.ReactiveProperty`1<bool>::get_Value()
      IL_000b:  ret
    } // end of method TargetInfo::get_enable

    .method public hidebysig specialname 
            instance void  set_enable(bool 'value') cil managed
    {
      // 代码大小       13 (0xd)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      class [UniRx]UniRx.BoolReactiveProperty Studio.FKCtrl/TargetInfo::_enable
      IL_0006:  ldarg.1
      IL_0007:  callvirt   instance void class [UniRx]UniRx.ReactiveProperty`1<bool>::set_Value(!0)
      IL_000c:  ret
    } // end of method TargetInfo::set_enable

    .method public hidebysig specialname rtspecialname 
            instance void  .ctor(class [UnityEngine.CoreModule]UnityEngine.GameObject _gameObject,
                                 class Studio.ChangeAmount _changeAmount,
                                 valuetype Studio.OIBoneInfo/BoneGroup _group,
                                 int32 _level,
                                 bool _boneWeight,
                                 int32 _boneID) cil managed
    {
      // 代码大小       126 (0x7e)
      .maxstack  3
      IL_0000:  ldarg.0
      IL_0001:  ldc.i4.1
      IL_0002:  newobj     instance void [UniRx]UniRx.BoolReactiveProperty::.ctor(bool)
      IL_0007:  stfld      class [UniRx]UniRx.BoolReactiveProperty Studio.FKCtrl/TargetInfo::_enable
      IL_000c:  ldarg.0
      IL_000d:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0012:  ldarg.0
      IL_0013:  ldarg.1
      IL_0014:  stfld      class [UnityEngine.CoreModule]UnityEngine.GameObject Studio.FKCtrl/TargetInfo::gameObject
      IL_0019:  ldarg.0
      IL_001a:  ldarg.2
      IL_001b:  stfld      class Studio.ChangeAmount Studio.FKCtrl/TargetInfo::changeAmount
      IL_0020:  ldarg.0
      IL_0021:  ldarg.3
      IL_0022:  call       instance void Studio.FKCtrl/TargetInfo::set_group(valuetype Studio.OIBoneInfo/BoneGroup)
      IL_0027:  ldarg.0
      IL_0028:  ldarg.s    _level
      IL_002a:  call       instance void Studio.FKCtrl/TargetInfo::set_level(int32)
      IL_002f:  ldarg.0
      IL_0030:  ldarg.s    _boneWeight
      IL_0032:  call       instance void Studio.FKCtrl/TargetInfo::set_boneWeight(bool)
      IL_0037:  ldarg.0
      IL_0038:  ldarg.s    _boneID
      IL_003a:  call       instance void Studio.FKCtrl/TargetInfo::set_boneID(int32)
      IL_003f:  ldarg.0
      IL_0040:  call       instance valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/TargetInfo::get_group()
      IL_0045:  ldc.i4     0x80
      IL_004a:  and
      IL_004b:  brtrue.s   IL_0065

      IL_004d:  ldarg.0
      IL_004e:  call       instance valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/TargetInfo::get_group()
      IL_0053:  ldc.i4     0x400
      IL_0058:  and
      IL_0059:  brtrue.s   IL_0065

      IL_005b:  ldarg.0
      IL_005c:  call       instance valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/TargetInfo::get_group()
      IL_0061:  ldc.i4.1
      IL_0062:  and
      IL_0063:  brfalse.s  IL_007d

      IL_0065:  ldarg.0
      IL_0066:  ldfld      class [UniRx]UniRx.BoolReactiveProperty Studio.FKCtrl/TargetInfo::_enable
      IL_006b:  ldarg.0
      IL_006c:  ldftn      instance void Studio.FKCtrl/TargetInfo::'<.ctor>b__26_0'(bool)
      IL_0072:  newobj     instance void class [mscorlib]System.Action`1<bool>::.ctor(object,
                                                                                      native int)
      IL_0077:  call       class [mscorlib]System.IDisposable [UniRx]UniRx.ObservableExtensions::Subscribe<bool>(class [mscorlib]System.IObservable`1<!!0>,
                                                                                                                 class [mscorlib]System.Action`1<!!0>)
      IL_007c:  pop
      IL_007d:  ret
    } // end of method TargetInfo::.ctor

    .method public hidebysig instance void 
            CopyBone() cil managed
    {
      // 代码大小       23 (0x17)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldfld      class Studio.ChangeAmount Studio.FKCtrl/TargetInfo::changeAmount
      IL_0006:  ldarg.0
      IL_0007:  call       instance class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl/TargetInfo::get_transform()
      IL_000c:  callvirt   instance valuetype [UnityEngine.CoreModule]UnityEngine.Vector3 [UnityEngine.CoreModule]UnityEngine.Transform::get_localEulerAngles()
      IL_0011:  callvirt   instance void Studio.ChangeAmount::set_rot(valuetype [UnityEngine.CoreModule]UnityEngine.Vector3)
      IL_0016:  ret
    } // end of method TargetInfo::CopyBone

    .method public hidebysig instance void 
            AddSyncBone(class [UnityEngine.CoreModule]UnityEngine.GameObject _gameObject) cil managed
    {
      // 代码大小       13 (0xd)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  ldarg.1
      IL_0002:  newobj     instance void Studio.OCIChar/SyncBoneInfo::.ctor(class [UnityEngine.CoreModule]UnityEngine.GameObject)
      IL_0007:  stfld      class Studio.OCIChar/SyncBoneInfo Studio.FKCtrl/TargetInfo::syncBoneInfo
      IL_000c:  ret
    } // end of method TargetInfo::AddSyncBone

    .method public hidebysig instance void 
            Update() cil managed
    {
      // 代码大小       67 (0x43)
      .maxstack  3
      IL_0000:  ldarg.0
      IL_0001:  call       instance bool Studio.FKCtrl/TargetInfo::get_enable()
      IL_0006:  ldarg.0
      IL_0007:  call       instance bool Studio.FKCtrl/TargetInfo::get_boneWeight()
      IL_000c:  and
      IL_000d:  brfalse.s  IL_0042

      IL_000f:  ldarg.0
      IL_0010:  call       instance class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl/TargetInfo::get_transform()
      IL_0015:  ldarg.0
      IL_0016:  ldfld      class Studio.ChangeAmount Studio.FKCtrl/TargetInfo::changeAmount
      IL_001b:  callvirt   instance valuetype [UnityEngine.CoreModule]UnityEngine.Vector3 Studio.ChangeAmount::get_rot()
      IL_0020:  call       valuetype [UnityEngine.CoreModule]UnityEngine.Quaternion [UnityEngine.CoreModule]UnityEngine.Quaternion::Euler(valuetype [UnityEngine.CoreModule]UnityEngine.Vector3)
      IL_0025:  callvirt   instance void [UnityEngine.CoreModule]UnityEngine.Transform::set_localRotation(valuetype [UnityEngine.CoreModule]UnityEngine.Quaternion)
      IL_002a:  ldarg.0
      IL_002b:  ldfld      class Studio.OCIChar/SyncBoneInfo Studio.FKCtrl/TargetInfo::syncBoneInfo
      IL_0030:  ldarg.0
      IL_0031:  ldftn      instance void Studio.FKCtrl/TargetInfo::'<Update>b__29_0'(class Studio.OCIChar/SyncBoneInfo)
      IL_0037:  newobj     instance void class [mscorlib]System.Action`1<class Studio.OCIChar/SyncBoneInfo>::.ctor(object,
                                                                                                                   native int)
      IL_003c:  call       bool [IL]NullCheck::SafeProc<class Studio.OCIChar/SyncBoneInfo>(!!0,
                                                                                           class [mscorlib]System.Action`1<!!0>)
      IL_0041:  pop
      IL_0042:  ret
    } // end of method TargetInfo::Update

    .method private hidebysig instance void 
            '<.ctor>b__26_0'(bool _b) cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       63 (0x3f)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  brtrue.s   IL_003e

      IL_0003:  ldarg.0
      IL_0004:  call       instance class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl/TargetInfo::get_transform()
      IL_0009:  call       valuetype [UnityEngine.CoreModule]UnityEngine.Quaternion [UnityEngine.CoreModule]UnityEngine.Quaternion::get_identity()
      IL_000e:  callvirt   instance void [UnityEngine.CoreModule]UnityEngine.Transform::set_localRotation(valuetype [UnityEngine.CoreModule]UnityEngine.Quaternion)
      IL_0013:  ldarg.0
      IL_0014:  ldfld      class Studio.OCIChar/SyncBoneInfo Studio.FKCtrl/TargetInfo::syncBoneInfo
      IL_0019:  ldsfld     class [mscorlib]System.Action`1<class Studio.OCIChar/SyncBoneInfo> Studio.FKCtrl/TargetInfo/'<>c'::'<>9__26_1'
      IL_001e:  dup
      IL_001f:  brtrue.s   IL_0038

      IL_0021:  pop
      IL_0022:  ldsfld     class Studio.FKCtrl/TargetInfo/'<>c' Studio.FKCtrl/TargetInfo/'<>c'::'<>9'
      IL_0027:  ldftn      instance void Studio.FKCtrl/TargetInfo/'<>c'::'<.ctor>b__26_1'(class Studio.OCIChar/SyncBoneInfo)
      IL_002d:  newobj     instance void class [mscorlib]System.Action`1<class Studio.OCIChar/SyncBoneInfo>::.ctor(object,
                                                                                                                   native int)
      IL_0032:  dup
      IL_0033:  stsfld     class [mscorlib]System.Action`1<class Studio.OCIChar/SyncBoneInfo> Studio.FKCtrl/TargetInfo/'<>c'::'<>9__26_1'
      IL_0038:  call       bool [IL]NullCheck::SafeProc<class Studio.OCIChar/SyncBoneInfo>(!!0,
                                                                                           class [mscorlib]System.Action`1<!!0>)
      IL_003d:  pop
      IL_003e:  ret
    } // end of method TargetInfo::'<.ctor>b__26_0'

    .method private hidebysig instance void 
            '<Update>b__29_0'(class Studio.OCIChar/SyncBoneInfo _sbi) cil managed
    {
      .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
      // 代码大小       18 (0x12)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldarg.0
      IL_0002:  call       instance class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl/TargetInfo::get_transform()
      IL_0007:  callvirt   instance valuetype [UnityEngine.CoreModule]UnityEngine.Quaternion [UnityEngine.CoreModule]UnityEngine.Transform::get_localRotation()
      IL_000c:  callvirt   instance void Studio.OCIChar/SyncBoneInfo::set_LocalRotation(valuetype [UnityEngine.CoreModule]UnityEngine.Quaternion)
      IL_0011:  ret
    } // end of method TargetInfo::'<Update>b__29_0'

    .property instance class [UnityEngine.CoreModule]UnityEngine.Transform
            transform()
    {
      .get instance class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl/TargetInfo::get_transform()
    } // end of property TargetInfo::transform
    .property instance valuetype Studio.OIBoneInfo/BoneGroup
            group()
    {
      .get instance valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/TargetInfo::get_group()
      .set instance void Studio.FKCtrl/TargetInfo::set_group(valuetype Studio.OIBoneInfo/BoneGroup)
    } // end of property TargetInfo::group
    .property instance int32 level()
    {
      .get instance int32 Studio.FKCtrl/TargetInfo::get_level()
      .set instance void Studio.FKCtrl/TargetInfo::set_level(int32)
    } // end of property TargetInfo::level
    .property instance bool boneWeight()
    {
      .get instance bool Studio.FKCtrl/TargetInfo::get_boneWeight()
      .set instance void Studio.FKCtrl/TargetInfo::set_boneWeight(bool)
    } // end of property TargetInfo::boneWeight
    .property instance int32 boneID()
    {
      .get instance int32 Studio.FKCtrl/TargetInfo::get_boneID()
      .set instance void Studio.FKCtrl/TargetInfo::set_boneID(int32)
    } // end of property TargetInfo::boneID
    .property instance bool enable()
    {
      .get instance bool Studio.FKCtrl/TargetInfo::get_enable()
      .set instance void Studio.FKCtrl/TargetInfo::set_enable(bool)
    } // end of property TargetInfo::enable
  } // end of class TargetInfo

  .class auto ansi sealed nested private beforefieldinit '<>c__DisplayClass10_0'
         extends [mscorlib]System.Object
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field public valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> v
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ret
    } // end of method '<>c__DisplayClass10_0'::.ctor

    .method assembly hidebysig instance bool 
            '<InitBones>b__0'(class Studio.OCIChar/BoneInfo _v) cil managed
    {
      // 代码大小       20 (0x14)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  callvirt   instance int32 Studio.OCIChar/BoneInfo::get_boneID()
      IL_0006:  ldarg.0
      IL_0007:  ldflda     valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_000c:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo>::get_Key()
      IL_0011:  ceq
      IL_0013:  ret
    } // end of method '<>c__DisplayClass10_0'::'<InitBones>b__0'

  } // end of class '<>c__DisplayClass10_0'

  .class auto ansi sealed nested private beforefieldinit '<>c__DisplayClass10_1'
         extends [mscorlib]System.Object
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field public bool boneWeight
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ret
    } // end of method '<>c__DisplayClass10_1'::.ctor

    .method assembly hidebysig instance void 
            '<InitBones>b__1'(class Studio.OCIChar/BoneInfo _v) cil managed
    {
      // 代码大小       13 (0xd)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldarg.0
      IL_0002:  ldfld      bool Studio.FKCtrl/'<>c__DisplayClass10_1'::boneWeight
      IL_0007:  callvirt   instance void Studio.OCIChar/BoneInfo::set_boneWeight(bool)
      IL_000c:  ret
    } // end of method '<>c__DisplayClass10_1'::'<InitBones>b__1'

  } // end of class '<>c__DisplayClass10_1'

  .class auto ansi sealed nested private beforefieldinit '<>c__DisplayClass12_0'
         extends [mscorlib]System.Object
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field public valuetype Studio.OIBoneInfo/BoneGroup _target
    .field public class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool> '<>9__0'
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ret
    } // end of method '<>c__DisplayClass12_0'::.ctor

    .method assembly hidebysig instance bool 
            '<CopyBone>b__0'(class Studio.FKCtrl/TargetInfo l) cil managed
    {
      // 代码大小       17 (0x11)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  callvirt   instance valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/TargetInfo::get_group()
      IL_0006:  ldarg.0
      IL_0007:  ldfld      valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/'<>c__DisplayClass12_0'::_target
      IL_000c:  and
      IL_000d:  ldc.i4.0
      IL_000e:  cgt.un
      IL_0010:  ret
    } // end of method '<>c__DisplayClass12_0'::'<CopyBone>b__0'

  } // end of class '<>c__DisplayClass12_0'

  .class auto ansi sealed nested private beforefieldinit '<>c__DisplayClass13_0'
         extends [mscorlib]System.Object
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field public valuetype Studio.OIBoneInfo/BoneGroup _group
    .field public class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool> '<>9__0'
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ret
    } // end of method '<>c__DisplayClass13_0'::.ctor

    .method assembly hidebysig instance bool 
            '<SetEnable>b__0'(class Studio.FKCtrl/TargetInfo l) cil managed
    {
      // 代码大小       17 (0x11)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  callvirt   instance valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/TargetInfo::get_group()
      IL_0006:  ldarg.0
      IL_0007:  ldfld      valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/'<>c__DisplayClass13_0'::_group
      IL_000c:  and
      IL_000d:  ldc.i4.0
      IL_000e:  cgt.un
      IL_0010:  ret
    } // end of method '<>c__DisplayClass13_0'::'<SetEnable>b__0'

  } // end of class '<>c__DisplayClass13_0'

  .class auto ansi sealed nested private beforefieldinit '<>c__DisplayClass14_0'
         extends [mscorlib]System.Object
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field public class Studio.FKCtrl/TargetInfo v
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ret
    } // end of method '<>c__DisplayClass14_0'::.ctor

    .method assembly hidebysig instance bool 
            '<ResetUsedBone>b__1'(class Studio.OCIChar/BoneInfo _v) cil managed
    {
      // 代码大小       20 (0x14)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  callvirt   instance int32 Studio.OCIChar/BoneInfo::get_boneID()
      IL_0006:  ldarg.0
      IL_0007:  ldfld      class Studio.FKCtrl/TargetInfo Studio.FKCtrl/'<>c__DisplayClass14_0'::v
      IL_000c:  callvirt   instance int32 Studio.FKCtrl/TargetInfo::get_boneID()
      IL_0011:  ceq
      IL_0013:  ret
    } // end of method '<>c__DisplayClass14_0'::'<ResetUsedBone>b__1'

  } // end of class '<>c__DisplayClass14_0'

  .class auto ansi sealed nested private beforefieldinit '<>c__DisplayClass14_1'
         extends [mscorlib]System.Object
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field public bool boneWeight
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ret
    } // end of method '<>c__DisplayClass14_1'::.ctor

    .method assembly hidebysig instance void 
            '<ResetUsedBone>b__2'(class Studio.OCIChar/BoneInfo _v) cil managed
    {
      // 代码大小       13 (0xd)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldarg.0
      IL_0002:  ldfld      bool Studio.FKCtrl/'<>c__DisplayClass14_1'::boneWeight
      IL_0007:  callvirt   instance void Studio.OCIChar/BoneInfo::set_boneWeight(bool)
      IL_000c:  ret
    } // end of method '<>c__DisplayClass14_1'::'<ResetUsedBone>b__2'

  } // end of class '<>c__DisplayClass14_1'

  .class auto ansi serializable sealed nested private beforefieldinit '<>c'
         extends [mscorlib]System.Object
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field public static initonly class Studio.FKCtrl/'<>c' '<>9'
    .field public static class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool> '<>9__14_0'
    .method private hidebysig specialname rtspecialname static 
            void  .cctor() cil managed
    {
      // 代码大小       11 (0xb)
      .maxstack  8
      IL_0000:  newobj     instance void Studio.FKCtrl/'<>c'::.ctor()
      IL_0005:  stsfld     class Studio.FKCtrl/'<>c' Studio.FKCtrl/'<>c'::'<>9'
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
            '<ResetUsedBone>b__14_0'(class Studio.FKCtrl/TargetInfo _v) cil managed
    {
      // 代码大小       14 (0xe)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  callvirt   instance valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/TargetInfo::get_group()
      IL_0006:  ldc.i4     0x400
      IL_000b:  ceq
      IL_000d:  ret
    } // end of method '<>c'::'<ResetUsedBone>b__14_0'

  } // end of class '<>c'

  .class auto ansi sealed nested private beforefieldinit '<>c__DisplayClass17_0'
         extends [mscorlib]System.Object
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    .field public class [UnityEngine.CoreModule]UnityEngine.Transform _transform
    .method public hidebysig specialname rtspecialname 
            instance void  .ctor() cil managed
    {
      // 代码大小       7 (0x7)
      .maxstack  8
      IL_0000:  ldarg.0
      IL_0001:  call       instance void [mscorlib]System.Object::.ctor()
      IL_0006:  ret
    } // end of method '<>c__DisplayClass17_0'::.ctor

    .method assembly hidebysig instance bool 
            '<UsedBone>b__0'(class [UnityEngine.CoreModule]UnityEngine.Transform _v) cil managed
    {
      // 代码大小       13 (0xd)
      .maxstack  8
      IL_0000:  ldarg.1
      IL_0001:  ldarg.0
      IL_0002:  ldfld      class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl/'<>c__DisplayClass17_0'::_transform
      IL_0007:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                        class [UnityEngine.CoreModule]UnityEngine.Object)
      IL_000c:  ret
    } // end of method '<>c__DisplayClass17_0'::'<UsedBone>b__0'

  } // end of class '<>c__DisplayClass17_0'

  .field public static valuetype Studio.OIBoneInfo/BoneGroup[] parts
  .field private class [UnityEngine.CoreModule]UnityEngine.Transform m_Transform
  .field private class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo> listBones
  .field private int32 '<count>k__BackingField'
  .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
  .method private hidebysig specialname instance class [UnityEngine.CoreModule]UnityEngine.Transform 
          get_transform() cil managed
  {
    // 代码大小       33 (0x21)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldfld      class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl::m_Transform
    IL_0006:  ldnull
    IL_0007:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_000c:  brfalse.s  IL_001a

    IL_000e:  ldarg.0
    IL_000f:  ldarg.0
    IL_0010:  call       instance class [UnityEngine.CoreModule]UnityEngine.Transform [UnityEngine.CoreModule]UnityEngine.Component::get_transform()
    IL_0015:  stfld      class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl::m_Transform
    IL_001a:  ldarg.0
    IL_001b:  ldfld      class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl::m_Transform
    IL_0020:  ret
  } // end of method FKCtrl::get_transform

  .method private hidebysig specialname instance int32 
          get_count() cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    // 代码大小       7 (0x7)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldfld      int32 Studio.FKCtrl::'<count>k__BackingField'
    IL_0006:  ret
  } // end of method FKCtrl::get_count

  .method private hidebysig specialname instance void 
          set_count(int32 'value') cil managed
  {
    .custom instance void [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::.ctor() = ( 01 00 00 00 ) 
    // 代码大小       8 (0x8)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  ldarg.1
    IL_0002:  stfld      int32 Studio.FKCtrl::'<count>k__BackingField'
    IL_0007:  ret
  } // end of method FKCtrl::set_count

  .method public hidebysig instance void 
          InitBones(class Studio.OCIChar _ociChar,
                    class Studio.OICharInfo _info,
                    class AIChara.ChaControl _chaControl,
                    class AIChara.ChaReference _charReference) cil managed
  {
    // 代码大小       717 (0x2cd)
    .maxstack  6
    .locals init (class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.FKCtrl/TargetInfo> V_0,
             valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.Info/BoneInfo> V_1,
             class Studio.FKCtrl/'<>c__DisplayClass10_0' V_2,
             class Studio.FKCtrl/'<>c__DisplayClass10_1' V_3,
             class [UnityEngine.CoreModule]UnityEngine.GameObject V_4,
             class Studio.FKCtrl/TargetInfo V_5,
             class Studio.OIBoneInfo V_6,
             valuetype Studio.OIBoneInfo/BoneGroup V_7,
             class Studio.FKCtrl/TargetInfo V_8,
             int32 V_9)
    IL_0000:  ldarg.2
    IL_0001:  brtrue.s   IL_0004

    IL_0003:  ret

    IL_0004:  ldarg.0
    IL_0005:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo> Studio.FKCtrl::listBones
    IL_000a:  callvirt   instance void class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo>::Clear()
    IL_000f:  newobj     instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.FKCtrl/TargetInfo>::.ctor()
    IL_0014:  stloc.0
    IL_0015:  call       !0 class [IL]Singleton`1<class Studio.Info>::get_Instance()
    IL_001a:  ldfld      class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/BoneInfo> Studio.Info::dicBoneInfo
    IL_001f:  callvirt   instance valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<!0,!1> class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.Info/BoneInfo>::GetEnumerator()
    IL_0024:  stloc.1
    .try
    {
      IL_0025:  br         IL_029f

      IL_002a:  newobj     instance void Studio.FKCtrl/'<>c__DisplayClass10_0'::.ctor()
      IL_002f:  stloc.2
      IL_0030:  ldloc.2
      IL_0031:  ldloca.s   V_1
      IL_0033:  call       instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.Info/BoneInfo>::get_Current()
      IL_0038:  stfld      valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_003d:  newobj     instance void Studio.FKCtrl/'<>c__DisplayClass10_1'::.ctor()
      IL_0042:  stloc.3
      IL_0043:  ldnull
      IL_0044:  stloc.s    V_4
      IL_0046:  ldloc.3
      IL_0047:  ldc.i4.1
      IL_0048:  stfld      bool Studio.FKCtrl/'<>c__DisplayClass10_1'::boneWeight
      IL_004d:  ldloc.2
      IL_004e:  ldflda     valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_0053:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo>::get_Value()
      IL_0058:  ldfld      int32 Studio.Info/BoneInfo::group
      IL_005d:  stloc.s    V_9
      IL_005f:  ldloc.s    V_9
      IL_0061:  ldc.i4.7
      IL_0062:  sub
      IL_0063:  ldc.i4.2
      IL_0064:  bgt.un.s   IL_0098

      IL_0066:  ldarg.s    _charReference
      IL_0068:  ldc.i4.0
      IL_0069:  callvirt   instance class [UnityEngine.CoreModule]UnityEngine.GameObject AIChara.ChaReference::GetReferenceInfo(valuetype AIChara.ChaReference/RefObjKey)
      IL_006e:  callvirt   instance class [UnityEngine.CoreModule]UnityEngine.Transform [UnityEngine.CoreModule]UnityEngine.GameObject::get_transform()
      IL_0073:  ldloc.2
      IL_0074:  ldflda     valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_0079:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo>::get_Value()
      IL_007e:  ldfld      string Studio.Info/BoneInfo::bone
      IL_0083:  call       class [UnityEngine.CoreModule]UnityEngine.Transform [IL]IllusionUtility.GetUtility.TransformFindEx::FindLoop(class [UnityEngine.CoreModule]UnityEngine.Transform,
                                                                                                                                        string)
      IL_0088:  dup
      IL_0089:  brtrue.s   IL_008f

      IL_008b:  pop
      IL_008c:  ldnull
      IL_008d:  br.s       IL_0094

      IL_008f:  call       instance class [UnityEngine.CoreModule]UnityEngine.GameObject [UnityEngine.CoreModule]UnityEngine.Component::get_gameObject()
      IL_0094:  stloc.s    V_4
      IL_0096:  br.s       IL_00ca

      IL_0098:  ldarg.0
      IL_0099:  call       instance class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl::get_transform()
      IL_009e:  ldloc.2
      IL_009f:  ldflda     valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_00a4:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo>::get_Value()
      IL_00a9:  ldfld      string Studio.Info/BoneInfo::bone
      IL_00ae:  call       class [UnityEngine.CoreModule]UnityEngine.Transform [IL]IllusionUtility.GetUtility.TransformFindEx::FindLoop(class [UnityEngine.CoreModule]UnityEngine.Transform,
                                                                                                                                        string)
      IL_00b3:  dup
      IL_00b4:  brtrue.s   IL_00ba

      IL_00b6:  pop
      IL_00b7:  ldnull
      IL_00b8:  br.s       IL_00bf

      IL_00ba:  call       instance class [UnityEngine.CoreModule]UnityEngine.GameObject [UnityEngine.CoreModule]UnityEngine.Component::get_gameObject()
      IL_00bf:  stloc.s    V_4
      IL_00c1:  ldloc.s    V_4
      IL_00c3:  ldnull
      IL_00c4:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                        class [UnityEngine.CoreModule]UnityEngine.Object)
      IL_00c9:  pop
      IL_00ca:  ldloc.s    V_4
      IL_00cc:  ldnull
      IL_00cd:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                        class [UnityEngine.CoreModule]UnityEngine.Object)
      IL_00d2:  brtrue     IL_029f

      IL_00d7:  ldnull
      IL_00d8:  stloc.s    V_5
      IL_00da:  ldloc.0
      IL_00db:  ldloc.2
      IL_00dc:  ldflda     valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_00e1:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo>::get_Value()
      IL_00e6:  ldfld      int32 Studio.Info/BoneInfo::sync
      IL_00eb:  ldloca.s   V_5
      IL_00ed:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.FKCtrl/TargetInfo>::TryGetValue(!0,
                                                                                                                                                    !1&)
      IL_00f2:  brfalse.s  IL_0102

      IL_00f4:  ldloc.s    V_5
      IL_00f6:  ldloc.s    V_4
      IL_00f8:  callvirt   instance void Studio.FKCtrl/TargetInfo::AddSyncBone(class [UnityEngine.CoreModule]UnityEngine.GameObject)
      IL_00fd:  br         IL_029f

      IL_0102:  ldnull
      IL_0103:  stloc.s    V_6
      IL_0105:  ldarg.2
      IL_0106:  callvirt   instance class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.OIBoneInfo> Studio.OICharInfo::get_bones()
      IL_010b:  ldloc.2
      IL_010c:  ldflda     valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_0111:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo>::get_Key()
      IL_0116:  ldloca.s   V_6
      IL_0118:  callvirt   instance bool class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.OIBoneInfo>::TryGetValue(!0,
                                                                                                                                             !1&)
      IL_011d:  brfalse    IL_029f

      IL_0122:  ldc.i4.1
      IL_0123:  stloc.s    V_7
      IL_0125:  ldloc.2
      IL_0126:  ldflda     valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_012b:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo>::get_Value()
      IL_0130:  ldfld      int32 Studio.Info/BoneInfo::group
      IL_0135:  stloc.s    V_9
      IL_0137:  ldloc.s    V_9
      IL_0139:  switch     ( 
                            IL_017b,
                            IL_017b,
                            IL_017b,
                            IL_017b,
                            IL_017b,
                            IL_0222,
                            IL_0222,
                            IL_0183,
                            IL_0183,
                            IL_0183,
                            IL_018f,
                            IL_019b,
                            IL_019b,
                            IL_01a7)
      IL_0176:  br         IL_0222

      IL_017b:  ldc.i4.1
      IL_017c:  stloc.s    V_7
      IL_017e:  br         IL_0239

      IL_0183:  ldc.i4     0x80
      IL_0188:  stloc.s    V_7
      IL_018a:  br         IL_0239

      IL_018f:  ldc.i4     0x100
      IL_0194:  stloc.s    V_7
      IL_0196:  br         IL_0239

      IL_019b:  ldc.i4     0x200
      IL_01a0:  stloc.s    V_7
      IL_01a2:  br         IL_0239

      IL_01a7:  ldloc.3
      IL_01a8:  ldc.i4.0
      IL_01a9:  stfld      bool Studio.FKCtrl/'<>c__DisplayClass10_1'::boneWeight
      IL_01ae:  ldloc.3
      IL_01af:  ldloc.3
      IL_01b0:  ldfld      bool Studio.FKCtrl/'<>c__DisplayClass10_1'::boneWeight
      IL_01b5:  ldarg.0
      IL_01b6:  ldarg.3
      IL_01b7:  ldc.i4.0
      IL_01b8:  callvirt   instance class AIChara.CmpClothes AIChara.ChaInfo::GetCustomClothesComponent(int32)
      IL_01bd:  ldloc.s    V_4
      IL_01bf:  callvirt   instance class [UnityEngine.CoreModule]UnityEngine.Transform [UnityEngine.CoreModule]UnityEngine.GameObject::get_transform()
      IL_01c4:  call       instance bool Studio.FKCtrl::UsedBone(class AIChara.CmpClothes,
                                                                 class [UnityEngine.CoreModule]UnityEngine.Transform)
      IL_01c9:  or
      IL_01ca:  stfld      bool Studio.FKCtrl/'<>c__DisplayClass10_1'::boneWeight
      IL_01cf:  ldloc.3
      IL_01d0:  ldloc.3
      IL_01d1:  ldfld      bool Studio.FKCtrl/'<>c__DisplayClass10_1'::boneWeight
      IL_01d6:  ldarg.0
      IL_01d7:  ldarg.3
      IL_01d8:  ldc.i4.1
      IL_01d9:  callvirt   instance class AIChara.CmpClothes AIChara.ChaInfo::GetCustomClothesComponent(int32)
      IL_01de:  ldloc.s    V_4
      IL_01e0:  callvirt   instance class [UnityEngine.CoreModule]UnityEngine.Transform [UnityEngine.CoreModule]UnityEngine.GameObject::get_transform()
      IL_01e5:  call       instance bool Studio.FKCtrl::UsedBone(class AIChara.CmpClothes,
                                                                 class [UnityEngine.CoreModule]UnityEngine.Transform)
      IL_01ea:  or
      IL_01eb:  stfld      bool Studio.FKCtrl/'<>c__DisplayClass10_1'::boneWeight
      IL_01f0:  ldc.i4     0x400
      IL_01f5:  stloc.s    V_7
      IL_01f7:  ldarg.1
      IL_01f8:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.OCIChar/BoneInfo> Studio.OCIChar::listBones
      IL_01fd:  ldloc.2
      IL_01fe:  ldftn      instance bool Studio.FKCtrl/'<>c__DisplayClass10_0'::'<InitBones>b__0'(class Studio.OCIChar/BoneInfo)
      IL_0204:  newobj     instance void class [mscorlib]System.Predicate`1<class Studio.OCIChar/BoneInfo>::.ctor(object,
                                                                                                                  native int)
      IL_0209:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<class Studio.OCIChar/BoneInfo>::Find(class [mscorlib]System.Predicate`1<!0>)
      IL_020e:  ldloc.3
      IL_020f:  ldftn      instance void Studio.FKCtrl/'<>c__DisplayClass10_1'::'<InitBones>b__1'(class Studio.OCIChar/BoneInfo)
      IL_0215:  newobj     instance void class [mscorlib]System.Action`1<class Studio.OCIChar/BoneInfo>::.ctor(object,
                                                                                                               native int)
      IL_021a:  call       bool [IL]NullCheck::SafeProc<class Studio.OCIChar/BoneInfo>(!!0,
                                                                                       class [mscorlib]System.Action`1<!!0>)
      IL_021f:  pop
      IL_0220:  br.s       IL_0239

      IL_0222:  ldc.i4.1
      IL_0223:  ldloc.2
      IL_0224:  ldflda     valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_0229:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo>::get_Value()
      IL_022e:  ldfld      int32 Studio.Info/BoneInfo::group
      IL_0233:  ldc.i4.s   31
      IL_0235:  and
      IL_0236:  shl
      IL_0237:  stloc.s    V_7
      IL_0239:  ldloc.s    V_4
      IL_023b:  ldloc.s    V_6
      IL_023d:  callvirt   instance class Studio.ChangeAmount Studio.ObjectInfo::get_changeAmount()
      IL_0242:  ldloc.s    V_7
      IL_0244:  ldloc.2
      IL_0245:  ldflda     valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_024a:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo>::get_Value()
      IL_024f:  ldfld      int32 Studio.Info/BoneInfo::level
      IL_0254:  ldloc.3
      IL_0255:  ldfld      bool Studio.FKCtrl/'<>c__DisplayClass10_1'::boneWeight
      IL_025a:  ldloc.2
      IL_025b:  ldflda     valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_0260:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo>::get_Key()
      IL_0265:  newobj     instance void Studio.FKCtrl/TargetInfo::.ctor(class [UnityEngine.CoreModule]UnityEngine.GameObject,
                                                                         class Studio.ChangeAmount,
                                                                         valuetype Studio.OIBoneInfo/BoneGroup,
                                                                         int32,
                                                                         bool,
                                                                         int32)
      IL_026a:  stloc.s    V_8
      IL_026c:  ldarg.0
      IL_026d:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo> Studio.FKCtrl::listBones
      IL_0272:  ldloc.s    V_8
      IL_0274:  callvirt   instance void class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo>::Add(!0)
      IL_0279:  ldloc.2
      IL_027a:  ldflda     valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_027f:  call       instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo>::get_Value()
      IL_0284:  ldfld      int32 Studio.Info/BoneInfo::sync
      IL_0289:  ldc.i4.m1
      IL_028a:  beq.s      IL_029f

      IL_028c:  ldloc.0
      IL_028d:  ldloc.2
      IL_028e:  ldflda     valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo> Studio.FKCtrl/'<>c__DisplayClass10_0'::v
      IL_0293:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<int32,class Studio.Info/BoneInfo>::get_Key()
      IL_0298:  ldloc.s    V_8
      IL_029a:  callvirt   instance void class [mscorlib]System.Collections.Generic.Dictionary`2<int32,class Studio.FKCtrl/TargetInfo>::Add(!0,
                                                                                                                                            !1)
      IL_029f:  ldloca.s   V_1
      IL_02a1:  call       instance bool valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.Info/BoneInfo>::MoveNext()
      IL_02a6:  brtrue     IL_002a

      IL_02ab:  leave.s    IL_02bb

    }  // end .try
    finally
    {
      IL_02ad:  ldloca.s   V_1
      IL_02af:  constrained. valuetype [mscorlib]System.Collections.Generic.Dictionary`2/Enumerator<int32,class Studio.Info/BoneInfo>
      IL_02b5:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_02ba:  endfinally
    }  // end handler
    IL_02bb:  ldarg.0
    IL_02bc:  ldarg.0
    IL_02bd:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo> Studio.FKCtrl::listBones
    IL_02c2:  callvirt   instance int32 class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo>::get_Count()
    IL_02c7:  call       instance void Studio.FKCtrl::set_count(int32)
    IL_02cc:  ret
  } // end of method FKCtrl::InitBones

  .method public hidebysig instance void 
          CopyBone() cil managed
  {
    // 代码大小       52 (0x34)
    .maxstack  1
    .locals init (valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class Studio.FKCtrl/TargetInfo> V_0)
    IL_0000:  ldarg.0
    IL_0001:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo> Studio.FKCtrl::listBones
    IL_0006:  callvirt   instance valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<!0> class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo>::GetEnumerator()
    IL_000b:  stloc.0
    .try
    {
      IL_000c:  br.s       IL_001a

      IL_000e:  ldloca.s   V_0
      IL_0010:  call       instance !0 valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class Studio.FKCtrl/TargetInfo>::get_Current()
      IL_0015:  callvirt   instance void Studio.FKCtrl/TargetInfo::CopyBone()
      IL_001a:  ldloca.s   V_0
      IL_001c:  call       instance bool valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class Studio.FKCtrl/TargetInfo>::MoveNext()
      IL_0021:  brtrue.s   IL_000e

      IL_0023:  leave.s    IL_0033

    }  // end .try
    finally
    {
      IL_0025:  ldloca.s   V_0
      IL_0027:  constrained. valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class Studio.FKCtrl/TargetInfo>
      IL_002d:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_0032:  endfinally
    }  // end handler
    IL_0033:  ret
  } // end of method FKCtrl::CopyBone

  .method public hidebysig instance void 
          CopyBone(valuetype Studio.OIBoneInfo/BoneGroup _target) cil managed
  {
    // 代码大小       95 (0x5f)
    .maxstack  4
    .locals init (class Studio.FKCtrl/'<>c__DisplayClass12_0' V_0,
             class [mscorlib]System.Collections.Generic.IEnumerator`1<class Studio.FKCtrl/TargetInfo> V_1,
             class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool> V_2)
    IL_0000:  newobj     instance void Studio.FKCtrl/'<>c__DisplayClass12_0'::.ctor()
    IL_0005:  stloc.0
    IL_0006:  ldloc.0
    IL_0007:  ldarg.1
    IL_0008:  stfld      valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/'<>c__DisplayClass12_0'::_target
    IL_000d:  ldarg.0
    IL_000e:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo> Studio.FKCtrl::listBones
    IL_0013:  ldloc.0
    IL_0014:  ldfld      class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool> Studio.FKCtrl/'<>c__DisplayClass12_0'::'<>9__0'
    IL_0019:  dup
    IL_001a:  brtrue.s   IL_0032

    IL_001c:  pop
    IL_001d:  ldloc.0
    IL_001e:  ldloc.0
    IL_001f:  ldftn      instance bool Studio.FKCtrl/'<>c__DisplayClass12_0'::'<CopyBone>b__0'(class Studio.FKCtrl/TargetInfo)
    IL_0025:  newobj     instance void class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool>::.ctor(object,
                                                                                                                 native int)
    IL_002a:  dup
    IL_002b:  stloc.2
    IL_002c:  stfld      class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool> Studio.FKCtrl/'<>c__DisplayClass12_0'::'<>9__0'
    IL_0031:  ldloc.2
    IL_0032:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Where<class Studio.FKCtrl/TargetInfo>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                  class [mscorlib]System.Func`2<!!0,bool>)
    IL_0037:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class Studio.FKCtrl/TargetInfo>::GetEnumerator()
    IL_003c:  stloc.1
    .try
    {
      IL_003d:  br.s       IL_004a

      IL_003f:  ldloc.1
      IL_0040:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class Studio.FKCtrl/TargetInfo>::get_Current()
      IL_0045:  callvirt   instance void Studio.FKCtrl/TargetInfo::CopyBone()
      IL_004a:  ldloc.1
      IL_004b:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_0050:  brtrue.s   IL_003f

      IL_0052:  leave.s    IL_005e

    }  // end .try
    finally
    {
      IL_0054:  ldloc.1
      IL_0055:  brfalse.s  IL_005d

      IL_0057:  ldloc.1
      IL_0058:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_005d:  endfinally
    }  // end handler
    IL_005e:  ret
  } // end of method FKCtrl::CopyBone

  .method public hidebysig instance void 
          SetEnable(valuetype Studio.OIBoneInfo/BoneGroup _group,
                    bool _enable) cil managed
  {
    // 代码大小       96 (0x60)
    .maxstack  4
    .locals init (class Studio.FKCtrl/'<>c__DisplayClass13_0' V_0,
             class [mscorlib]System.Collections.Generic.IEnumerator`1<class Studio.FKCtrl/TargetInfo> V_1,
             class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool> V_2)
    IL_0000:  newobj     instance void Studio.FKCtrl/'<>c__DisplayClass13_0'::.ctor()
    IL_0005:  stloc.0
    IL_0006:  ldloc.0
    IL_0007:  ldarg.1
    IL_0008:  stfld      valuetype Studio.OIBoneInfo/BoneGroup Studio.FKCtrl/'<>c__DisplayClass13_0'::_group
    IL_000d:  ldarg.0
    IL_000e:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo> Studio.FKCtrl::listBones
    IL_0013:  ldloc.0
    IL_0014:  ldfld      class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool> Studio.FKCtrl/'<>c__DisplayClass13_0'::'<>9__0'
    IL_0019:  dup
    IL_001a:  brtrue.s   IL_0032

    IL_001c:  pop
    IL_001d:  ldloc.0
    IL_001e:  ldloc.0
    IL_001f:  ldftn      instance bool Studio.FKCtrl/'<>c__DisplayClass13_0'::'<SetEnable>b__0'(class Studio.FKCtrl/TargetInfo)
    IL_0025:  newobj     instance void class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool>::.ctor(object,
                                                                                                                 native int)
    IL_002a:  dup
    IL_002b:  stloc.2
    IL_002c:  stfld      class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool> Studio.FKCtrl/'<>c__DisplayClass13_0'::'<>9__0'
    IL_0031:  ldloc.2
    IL_0032:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Where<class Studio.FKCtrl/TargetInfo>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                  class [mscorlib]System.Func`2<!!0,bool>)
    IL_0037:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class Studio.FKCtrl/TargetInfo>::GetEnumerator()
    IL_003c:  stloc.1
    .try
    {
      IL_003d:  br.s       IL_004b

      IL_003f:  ldloc.1
      IL_0040:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class Studio.FKCtrl/TargetInfo>::get_Current()
      IL_0045:  ldarg.2
      IL_0046:  callvirt   instance void Studio.FKCtrl/TargetInfo::set_enable(bool)
      IL_004b:  ldloc.1
      IL_004c:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_0051:  brtrue.s   IL_003f

      IL_0053:  leave.s    IL_005f

    }  // end .try
    finally
    {
      IL_0055:  ldloc.1
      IL_0056:  brfalse.s  IL_005e

      IL_0058:  ldloc.1
      IL_0059:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_005e:  endfinally
    }  // end handler
    IL_005f:  ret
  } // end of method FKCtrl::SetEnable

  .method public hidebysig instance void 
          ResetUsedBone(class Studio.OCIChar _ociChar) cil managed
  {
    // 代码大小       247 (0xf7)
    .maxstack  5
    .locals init (class AIChara.ChaControl V_0,
             class [mscorlib]System.Collections.Generic.IEnumerator`1<class Studio.FKCtrl/TargetInfo> V_1,
             class Studio.FKCtrl/'<>c__DisplayClass14_0' V_2,
             class Studio.FKCtrl/'<>c__DisplayClass14_1' V_3)
    IL_0000:  ldarg.1
    IL_0001:  ldfld      class AIChara.ChaControl Studio.OCIChar::charInfo
    IL_0006:  stloc.0
    IL_0007:  ldarg.0
    IL_0008:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo> Studio.FKCtrl::listBones
    IL_000d:  ldsfld     class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool> Studio.FKCtrl/'<>c'::'<>9__14_0'
    IL_0012:  dup
    IL_0013:  brtrue.s   IL_002c

    IL_0015:  pop
    IL_0016:  ldsfld     class Studio.FKCtrl/'<>c' Studio.FKCtrl/'<>c'::'<>9'
    IL_001b:  ldftn      instance bool Studio.FKCtrl/'<>c'::'<ResetUsedBone>b__14_0'(class Studio.FKCtrl/TargetInfo)
    IL_0021:  newobj     instance void class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool>::.ctor(object,
                                                                                                                 native int)
    IL_0026:  dup
    IL_0027:  stsfld     class [mscorlib]System.Func`2<class Studio.FKCtrl/TargetInfo,bool> Studio.FKCtrl/'<>c'::'<>9__14_0'
    IL_002c:  call       class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0> [System.Core]System.Linq.Enumerable::Where<class Studio.FKCtrl/TargetInfo>(class [mscorlib]System.Collections.Generic.IEnumerable`1<!!0>,
                                                                                                                                                                  class [mscorlib]System.Func`2<!!0,bool>)
    IL_0031:  callvirt   instance class [mscorlib]System.Collections.Generic.IEnumerator`1<!0> class [mscorlib]System.Collections.Generic.IEnumerable`1<class Studio.FKCtrl/TargetInfo>::GetEnumerator()
    IL_0036:  stloc.1
    .try
    {
      IL_0037:  br         IL_00df

      IL_003c:  newobj     instance void Studio.FKCtrl/'<>c__DisplayClass14_0'::.ctor()
      IL_0041:  stloc.2
      IL_0042:  ldloc.2
      IL_0043:  ldloc.1
      IL_0044:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.IEnumerator`1<class Studio.FKCtrl/TargetInfo>::get_Current()
      IL_0049:  stfld      class Studio.FKCtrl/TargetInfo Studio.FKCtrl/'<>c__DisplayClass14_0'::v
      IL_004e:  newobj     instance void Studio.FKCtrl/'<>c__DisplayClass14_1'::.ctor()
      IL_0053:  stloc.3
      IL_0054:  ldloc.3
      IL_0055:  ldc.i4.0
      IL_0056:  stfld      bool Studio.FKCtrl/'<>c__DisplayClass14_1'::boneWeight
      IL_005b:  ldloc.3
      IL_005c:  ldloc.3
      IL_005d:  ldfld      bool Studio.FKCtrl/'<>c__DisplayClass14_1'::boneWeight
      IL_0062:  ldarg.0
      IL_0063:  ldloc.0
      IL_0064:  ldc.i4.0
      IL_0065:  callvirt   instance class AIChara.CmpClothes AIChara.ChaInfo::GetCustomClothesComponent(int32)
      IL_006a:  ldloc.2
      IL_006b:  ldfld      class Studio.FKCtrl/TargetInfo Studio.FKCtrl/'<>c__DisplayClass14_0'::v
      IL_0070:  callvirt   instance class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl/TargetInfo::get_transform()
      IL_0075:  call       instance bool Studio.FKCtrl::UsedBone(class AIChara.CmpClothes,
                                                                 class [UnityEngine.CoreModule]UnityEngine.Transform)
      IL_007a:  or
      IL_007b:  stfld      bool Studio.FKCtrl/'<>c__DisplayClass14_1'::boneWeight
      IL_0080:  ldloc.3
      IL_0081:  ldloc.3
      IL_0082:  ldfld      bool Studio.FKCtrl/'<>c__DisplayClass14_1'::boneWeight
      IL_0087:  ldarg.0
      IL_0088:  ldloc.0
      IL_0089:  ldc.i4.1
      IL_008a:  callvirt   instance class AIChara.CmpClothes AIChara.ChaInfo::GetCustomClothesComponent(int32)
      IL_008f:  ldloc.2
      IL_0090:  ldfld      class Studio.FKCtrl/TargetInfo Studio.FKCtrl/'<>c__DisplayClass14_0'::v
      IL_0095:  callvirt   instance class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl/TargetInfo::get_transform()
      IL_009a:  call       instance bool Studio.FKCtrl::UsedBone(class AIChara.CmpClothes,
                                                                 class [UnityEngine.CoreModule]UnityEngine.Transform)
      IL_009f:  or
      IL_00a0:  stfld      bool Studio.FKCtrl/'<>c__DisplayClass14_1'::boneWeight
      IL_00a5:  ldarg.1
      IL_00a6:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.OCIChar/BoneInfo> Studio.OCIChar::listBones
      IL_00ab:  ldloc.2
      IL_00ac:  ldftn      instance bool Studio.FKCtrl/'<>c__DisplayClass14_0'::'<ResetUsedBone>b__1'(class Studio.OCIChar/BoneInfo)
      IL_00b2:  newobj     instance void class [mscorlib]System.Predicate`1<class Studio.OCIChar/BoneInfo>::.ctor(object,
                                                                                                                  native int)
      IL_00b7:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<class Studio.OCIChar/BoneInfo>::Find(class [mscorlib]System.Predicate`1<!0>)
      IL_00bc:  ldloc.3
      IL_00bd:  ldftn      instance void Studio.FKCtrl/'<>c__DisplayClass14_1'::'<ResetUsedBone>b__2'(class Studio.OCIChar/BoneInfo)
      IL_00c3:  newobj     instance void class [mscorlib]System.Action`1<class Studio.OCIChar/BoneInfo>::.ctor(object,
                                                                                                               native int)
      IL_00c8:  call       bool [IL]NullCheck::SafeProc<class Studio.OCIChar/BoneInfo>(!!0,
                                                                                       class [mscorlib]System.Action`1<!!0>)
      IL_00cd:  pop
      IL_00ce:  ldloc.2
      IL_00cf:  ldfld      class Studio.FKCtrl/TargetInfo Studio.FKCtrl/'<>c__DisplayClass14_0'::v
      IL_00d4:  ldloc.3
      IL_00d5:  ldfld      bool Studio.FKCtrl/'<>c__DisplayClass14_1'::boneWeight
      IL_00da:  callvirt   instance void Studio.FKCtrl/TargetInfo::set_boneWeight(bool)
      IL_00df:  ldloc.1
      IL_00e0:  callvirt   instance bool [mscorlib]System.Collections.IEnumerator::MoveNext()
      IL_00e5:  brtrue     IL_003c

      IL_00ea:  leave.s    IL_00f6

    }  // end .try
    finally
    {
      IL_00ec:  ldloc.1
      IL_00ed:  brfalse.s  IL_00f5

      IL_00ef:  ldloc.1
      IL_00f0:  callvirt   instance void [mscorlib]System.IDisposable::Dispose()
      IL_00f5:  endfinally
    }  // end handler
    IL_00f6:  ret
  } // end of method FKCtrl::ResetUsedBone

  .method private hidebysig instance bool 
          UsedBone(class AIChara.CmpClothes _cmpClothes,
                   class [UnityEngine.CoreModule]UnityEngine.Transform _transform) cil managed
  {
    // 代码大小       63 (0x3f)
    .maxstack  4
    .locals init (bool V_0)
    IL_0000:  ldc.i4.0
    IL_0001:  stloc.0
    IL_0002:  ldarg.1
    IL_0003:  ldnull
    IL_0004:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0009:  brfalse.s  IL_000d

    IL_000b:  ldc.i4.0
    IL_000c:  ret

    IL_000d:  ldloc.0
    IL_000e:  ldarg.0
    IL_000f:  ldarg.1
    IL_0010:  ldfld      class [UnityEngine.CoreModule]UnityEngine.Renderer[] AIChara.CmpClothes::rendNormal01
    IL_0015:  ldarg.2
    IL_0016:  call       instance bool Studio.FKCtrl::UsedBone(class [UnityEngine.CoreModule]UnityEngine.Renderer[],
                                                               class [UnityEngine.CoreModule]UnityEngine.Transform)
    IL_001b:  or
    IL_001c:  stloc.0
    IL_001d:  ldloc.0
    IL_001e:  ldarg.0
    IL_001f:  ldarg.1
    IL_0020:  ldfld      class [UnityEngine.CoreModule]UnityEngine.Renderer[] AIChara.CmpClothes::rendNormal02
    IL_0025:  ldarg.2
    IL_0026:  call       instance bool Studio.FKCtrl::UsedBone(class [UnityEngine.CoreModule]UnityEngine.Renderer[],
                                                               class [UnityEngine.CoreModule]UnityEngine.Transform)
    IL_002b:  or
    IL_002c:  stloc.0
    IL_002d:  ldloc.0
    IL_002e:  ldarg.0
    IL_002f:  ldarg.1
    IL_0030:  ldfld      class [UnityEngine.CoreModule]UnityEngine.Renderer[] AIChara.CmpClothes::rendNormal03
    IL_0035:  ldarg.2
    IL_0036:  call       instance bool Studio.FKCtrl::UsedBone(class [UnityEngine.CoreModule]UnityEngine.Renderer[],
                                                               class [UnityEngine.CoreModule]UnityEngine.Transform)
    IL_003b:  or
    IL_003c:  stloc.0
    IL_003d:  ldloc.0
    IL_003e:  ret
  } // end of method FKCtrl::UsedBone

  .method private hidebysig instance bool 
          UsedBone(class [UnityEngine.CoreModule]UnityEngine.Renderer[] _renderers,
                   class [UnityEngine.CoreModule]UnityEngine.Transform _transform) cil managed
  {
    // 代码大小       49 (0x31)
    .maxstack  3
    .locals init (class [UnityEngine.CoreModule]UnityEngine.Renderer[] V_0,
             int32 V_1,
             class [UnityEngine.CoreModule]UnityEngine.Renderer V_2)
    IL_0000:  ldarg.1
    IL_0001:  call       bool [IL]NullCheck::IsNullOrEmpty<class [UnityEngine.CoreModule]UnityEngine.Renderer>(class [mscorlib]System.Collections.Generic.IReadOnlyCollection`1<!!0>)
    IL_0006:  brfalse.s  IL_000a

    IL_0008:  ldc.i4.0
    IL_0009:  ret

    IL_000a:  ldarg.1
    IL_000b:  stloc.0
    IL_000c:  ldc.i4.0
    IL_000d:  stloc.1
    IL_000e:  br.s       IL_0029

    IL_0010:  ldloc.0
    IL_0011:  ldloc.1
    IL_0012:  ldelem.ref
    IL_0013:  stloc.2
    IL_0014:  ldarg.0
    IL_0015:  ldloc.2
    IL_0016:  isinst     [UnityEngine.CoreModule]UnityEngine.SkinnedMeshRenderer
    IL_001b:  ldarg.2
    IL_001c:  call       instance bool Studio.FKCtrl::UsedBone(class [UnityEngine.CoreModule]UnityEngine.SkinnedMeshRenderer,
                                                               class [UnityEngine.CoreModule]UnityEngine.Transform)
    IL_0021:  brfalse.s  IL_0025

    IL_0023:  ldc.i4.1
    IL_0024:  ret

    IL_0025:  ldloc.1
    IL_0026:  ldc.i4.1
    IL_0027:  add
    IL_0028:  stloc.1
    IL_0029:  ldloc.1
    IL_002a:  ldloc.0
    IL_002b:  ldlen
    IL_002c:  conv.i4
    IL_002d:  blt.s      IL_0010

    IL_002f:  ldc.i4.0
    IL_0030:  ret
  } // end of method FKCtrl::UsedBone

  .method private hidebysig instance bool 
          UsedBone(class [UnityEngine.CoreModule]UnityEngine.SkinnedMeshRenderer _renderer,
                   class [UnityEngine.CoreModule]UnityEngine.Transform _transform) cil managed
  {
    // 代码大小       207 (0xcf)
    .maxstack  3
    .locals init (class Studio.FKCtrl/'<>c__DisplayClass17_0' V_0,
             int32 V_1,
             valuetype [UnityEngine.CoreModule]UnityEngine.BoneWeight[] V_2,
             int32 V_3,
             valuetype [UnityEngine.CoreModule]UnityEngine.BoneWeight V_4)
    IL_0000:  newobj     instance void Studio.FKCtrl/'<>c__DisplayClass17_0'::.ctor()
    IL_0005:  stloc.0
    IL_0006:  ldloc.0
    IL_0007:  ldarg.2
    IL_0008:  stfld      class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl/'<>c__DisplayClass17_0'::_transform
    IL_000d:  ldarg.1
    IL_000e:  ldnull
    IL_000f:  call       bool [UnityEngine.CoreModule]UnityEngine.Object::op_Equality(class [UnityEngine.CoreModule]UnityEngine.Object,
                                                                                      class [UnityEngine.CoreModule]UnityEngine.Object)
    IL_0014:  brfalse.s  IL_0018

    IL_0016:  ldc.i4.0
    IL_0017:  ret

    IL_0018:  ldarg.1
    IL_0019:  callvirt   instance class [UnityEngine.CoreModule]UnityEngine.Transform[] [UnityEngine.CoreModule]UnityEngine.SkinnedMeshRenderer::get_bones()
    IL_001e:  ldloc.0
    IL_001f:  ldftn      instance bool Studio.FKCtrl/'<>c__DisplayClass17_0'::'<UsedBone>b__0'(class [UnityEngine.CoreModule]UnityEngine.Transform)
    IL_0025:  newobj     instance void class [mscorlib]System.Predicate`1<class [UnityEngine.CoreModule]UnityEngine.Transform>::.ctor(object,
                                                                                                                                      native int)
    IL_002a:  call       int32 [mscorlib]System.Array::FindIndex<class [UnityEngine.CoreModule]UnityEngine.Transform>(!!0[],
                                                                                                                      class [mscorlib]System.Predicate`1<!!0>)
    IL_002f:  stloc.1
    IL_0030:  ldloc.1
    IL_0031:  ldc.i4.0
    IL_0032:  blt        IL_00cd

    IL_0037:  ldarg.1
    IL_0038:  callvirt   instance class [UnityEngine.CoreModule]UnityEngine.Mesh [UnityEngine.CoreModule]UnityEngine.SkinnedMeshRenderer::get_sharedMesh()
    IL_003d:  callvirt   instance valuetype [UnityEngine.CoreModule]UnityEngine.BoneWeight[] [UnityEngine.CoreModule]UnityEngine.Mesh::get_boneWeights()
    IL_0042:  stloc.2
    IL_0043:  ldc.i4.0
    IL_0044:  stloc.3
    IL_0045:  br.s       IL_00c4

    IL_0047:  ldloc.2
    IL_0048:  ldloc.3
    IL_0049:  ldelem     [UnityEngine.CoreModule]UnityEngine.BoneWeight
    IL_004e:  stloc.s    V_4
    IL_0050:  ldloca.s   V_4
    IL_0052:  call       instance int32 [UnityEngine.CoreModule]UnityEngine.BoneWeight::get_boneIndex0()
    IL_0057:  ldloc.1
    IL_0058:  bne.un.s   IL_006c

    IL_005a:  ldloca.s   V_4
    IL_005c:  call       instance float32 [UnityEngine.CoreModule]UnityEngine.BoneWeight::get_weight0()
    IL_0061:  ldc.r4     0.0
    IL_0066:  ceq
    IL_0068:  ldc.i4.0
    IL_0069:  ceq
    IL_006b:  ret

    IL_006c:  ldloca.s   V_4
    IL_006e:  call       instance int32 [UnityEngine.CoreModule]UnityEngine.BoneWeight::get_boneIndex1()
    IL_0073:  ldloc.1
    IL_0074:  bne.un.s   IL_0088

    IL_0076:  ldloca.s   V_4
    IL_0078:  call       instance float32 [UnityEngine.CoreModule]UnityEngine.BoneWeight::get_weight1()
    IL_007d:  ldc.r4     0.0
    IL_0082:  ceq
    IL_0084:  ldc.i4.0
    IL_0085:  ceq
    IL_0087:  ret

    IL_0088:  ldloca.s   V_4
    IL_008a:  call       instance int32 [UnityEngine.CoreModule]UnityEngine.BoneWeight::get_boneIndex2()
    IL_008f:  ldloc.1
    IL_0090:  bne.un.s   IL_00a4

    IL_0092:  ldloca.s   V_4
    IL_0094:  call       instance float32 [UnityEngine.CoreModule]UnityEngine.BoneWeight::get_weight2()
    IL_0099:  ldc.r4     0.0
    IL_009e:  ceq
    IL_00a0:  ldc.i4.0
    IL_00a1:  ceq
    IL_00a3:  ret

    IL_00a4:  ldloca.s   V_4
    IL_00a6:  call       instance int32 [UnityEngine.CoreModule]UnityEngine.BoneWeight::get_boneIndex3()
    IL_00ab:  ldloc.1
    IL_00ac:  bne.un.s   IL_00c0

    IL_00ae:  ldloca.s   V_4
    IL_00b0:  call       instance float32 [UnityEngine.CoreModule]UnityEngine.BoneWeight::get_weight3()
    IL_00b5:  ldc.r4     0.0
    IL_00ba:  ceq
    IL_00bc:  ldc.i4.0
    IL_00bd:  ceq
    IL_00bf:  ret

    IL_00c0:  ldloc.3
    IL_00c1:  ldc.i4.1
    IL_00c2:  add
    IL_00c3:  stloc.3
    IL_00c4:  ldloc.3
    IL_00c5:  ldloc.2
    IL_00c6:  ldlen
    IL_00c7:  conv.i4
    IL_00c8:  blt        IL_0047

    IL_00cd:  ldc.i4.0
    IL_00ce:  ret
  } // end of method FKCtrl::UsedBone

  .method private hidebysig instance void 
          LateUpdate() cil managed
  {
    // 代码大小       35 (0x23)
    .maxstack  2
    .locals init (int32 V_0)
    IL_0000:  ldc.i4.0
    IL_0001:  stloc.0
    IL_0002:  br.s       IL_0019

    IL_0004:  ldarg.0
    IL_0005:  ldfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo> Studio.FKCtrl::listBones
    IL_000a:  ldloc.0
    IL_000b:  callvirt   instance !0 class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo>::get_Item(int32)
    IL_0010:  callvirt   instance void Studio.FKCtrl/TargetInfo::Update()
    IL_0015:  ldloc.0
    IL_0016:  ldc.i4.1
    IL_0017:  add
    IL_0018:  stloc.0
    IL_0019:  ldloc.0
    IL_001a:  ldarg.0
    IL_001b:  call       instance int32 Studio.FKCtrl::get_count()
    IL_0020:  blt.s      IL_0004

    IL_0022:  ret
  } // end of method FKCtrl::LateUpdate

  .method public hidebysig specialname rtspecialname 
          instance void  .ctor() cil managed
  {
    // 代码大小       18 (0x12)
    .maxstack  8
    IL_0000:  ldarg.0
    IL_0001:  newobj     instance void class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo>::.ctor()
    IL_0006:  stfld      class [mscorlib]System.Collections.Generic.List`1<class Studio.FKCtrl/TargetInfo> Studio.FKCtrl::listBones
    IL_000b:  ldarg.0
    IL_000c:  call       instance void [UnityEngine.CoreModule]UnityEngine.MonoBehaviour::.ctor()
    IL_0011:  ret
  } // end of method FKCtrl::.ctor

  .method private hidebysig specialname rtspecialname static 
          void  .cctor() cil managed
  {
    // 代码大小       23 (0x17)
    .maxstack  8
    IL_0000:  ldc.i4.7
    IL_0001:  newarr     Studio.OIBoneInfo/BoneGroup
    IL_0006:  dup
    IL_0007:  ldtoken    field valuetype '<PrivateImplementationDetails>'/'__StaticArrayInitTypeSize=28' '<PrivateImplementationDetails>'::'6F9EAAF0F07F6646DACD2F91A6603E16CE7A3095'
    IL_000c:  call       void [mscorlib]System.Runtime.CompilerServices.RuntimeHelpers::InitializeArray(class [mscorlib]System.Array,
                                                                                                        valuetype [mscorlib]System.RuntimeFieldHandle)
    IL_0011:  stsfld     valuetype Studio.OIBoneInfo/BoneGroup[] Studio.FKCtrl::parts
    IL_0016:  ret
  } // end of method FKCtrl::.cctor

  .property instance class [UnityEngine.CoreModule]UnityEngine.Transform
          transform()
  {
    .get instance class [UnityEngine.CoreModule]UnityEngine.Transform Studio.FKCtrl::get_transform()
  } // end of property FKCtrl::transform
  .property instance int32 count()
  {
    .get instance int32 Studio.FKCtrl::get_count()
    .set instance void Studio.FKCtrl::set_count(int32)
  } // end of property FKCtrl::count
} // end of class Studio.FKCtrl

// *********** 反汇编完成 ***********************
// 警告: 创建了 Win32 资源文件 tmp/Assembly-CSharp.res
