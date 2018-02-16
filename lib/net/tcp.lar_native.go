package LARVA_NATIVE

import (
    "net"
    "io"
)

type lar_cls_3_net_12__TcpListener struct {
    ntl *net.TCPListener
}

func lar_new_obj_lar_cls_3_net_12__TcpListener(addr *lar_cls_10___builtins_6_String) *lar_cls_3_net_12__TcpListener {
    tcp_addr, err := net.ResolveTCPAddr("tcp", lar_util_convert_lar_str_to_go_str(addr))
    if err != nil {
        lar_func_10___builtins_5_throw(lar_new_obj_lar_cls_3_net_11_ListenError(lar_util_create_lar_str_from_go_str(err.Error())))
    }
    ntl, err := net.ListenTCP("tcp", tcp_addr)
    if err != nil {
        lar_func_10___builtins_5_throw(lar_new_obj_lar_cls_3_net_11_ListenError(lar_util_create_lar_str_from_go_str(err.Error())))
    }
    return &lar_cls_3_net_12__TcpListener{ntl: ntl}
}

func (this *lar_cls_3_net_12__TcpListener) method_get_addr() *lar_cls_10___builtins_6_String {
    return lar_util_create_lar_str_from_go_str(this.ntl.Addr().String())
}

func (this *lar_cls_3_net_12__TcpListener) method_accept() *lar_cls_3_net_7_TcpConn {
    ntc, err := this.ntl.AcceptTCP()
    if err != nil {
        lar_func_10___builtins_5_throw(lar_new_obj_lar_cls_3_net_11_AcceptError(lar_util_create_lar_str_from_go_str(err.Error())))
    }
    return &lar_cls_3_net_7_TcpConn{
        m_tc: &lar_cls_3_net_8__TcpConn{
            ntc: ntc,
        },
    }
}

func (this *lar_cls_3_net_12__TcpListener) method_close() {
    this.ntl.Close()
}

type lar_cls_3_net_8__TcpConn struct {
    ntc *net.TCPConn
}

func (this *lar_cls_3_net_8__TcpConn) method_get_local_addr() *lar_cls_10___builtins_6_String {
    return lar_util_create_lar_str_from_go_str(this.ntc.LocalAddr().String())
}

func (this *lar_cls_3_net_8__TcpConn) method_get_remote_addr() *lar_cls_10___builtins_6_String {
    return lar_util_create_lar_str_from_go_str(this.ntc.RemoteAddr().String())
}

func (this *lar_cls_3_net_8__TcpConn) method_send(buf *[]uint8, begin, length int64) {
    buf_len := int64(len(*buf))
    end := begin + length
    if begin < 0 || begin > buf_len || end < 0 || end > buf_len || end < begin {
        lar_func_10___builtins_5_throw(lar_new_obj_lar_cls_3_net_9_SendError(lar_util_create_lar_str_from_go_str("无效的输入数据")))
    }
    send_buf := (*buf)[begin : end]

    _, err := this.ntc.Write(send_buf)
    if err != nil {
        lar_func_10___builtins_5_throw(lar_new_obj_lar_cls_3_net_9_SendError(lar_util_create_lar_str_from_go_str(err.Error())))
    }
}

func (this *lar_cls_3_net_8__TcpConn) method_recv(buf *[]uint8, begin, length int64) int64 {
    buf_len := int64(len(*buf))
    end := begin + length
    if begin < 0 || begin > buf_len || end < 0 || end > buf_len || end < begin {
        lar_func_10___builtins_5_throw(lar_new_obj_lar_cls_3_net_9_RecvError(lar_util_create_lar_str_from_go_str("无效的输入数据")))
    }
    recv_buf := (*buf)[begin : end]

    recved_len, err := this.ntc.Read(recv_buf)
    if err != nil {
        if err == io.EOF {
            return 0
        }
        lar_func_10___builtins_5_throw(lar_new_obj_lar_cls_3_net_9_RecvError(lar_util_create_lar_str_from_go_str(err.Error())))
    }
    return int64(recved_len)
}

func (this *lar_cls_3_net_8__TcpConn) method_close() {
    this.ntc.Close()
}
