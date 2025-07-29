# KVM Switch Controller

Home Assistant集成，用于控制KVM切换器的输入源选择。

## 功能
- 通过选择器实体切换KVM输出端口的输入源

## 安装
1. 将此目录复制到Home Assistant的`custom_components/kvm_switch`
2. 重启Home Assistant
3. 在集成页面添加"KVM Switch Controller"

## 配置
- 主机IP: KVM切换器的网络地址
- 端口: 通信端口(默认5000)
- 输出端口数量: 切换器的输出端口数

## 实体
- 选择器: `select.outX_source` - 控制每个输出端口的输入源

## 开发
[GitHub仓库](https://github.com/chaosl1996/kvm_switch)