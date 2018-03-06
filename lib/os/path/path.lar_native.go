package LARVA_NATIVE

import (
    "path/filepath"
)

func lar_func_2_2_os_4_path_9_base_name(path *lar_cls_10___builtins_6_String) *lar_cls_10___builtins_6_String {
    return lar_util_create_lar_str_from_go_str(filepath.Base(lar_util_convert_lar_str_to_go_str(path)))
}

func lar_func_2_2_os_4_path_8_dir_name(path *lar_cls_10___builtins_6_String) *lar_cls_10___builtins_6_String {
    return lar_util_create_lar_str_from_go_str(filepath.Dir(lar_util_convert_lar_str_to_go_str(path)))
}
