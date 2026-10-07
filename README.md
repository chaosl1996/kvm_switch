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

---

<!-- DONATE:START -->
## ☕ 请作者喝杯咖啡

如果这些项目对你有帮助，欢迎请我喝一杯咖啡，或顺手点个 Star 支持一下～

<p align="center">
  <img src="https://cdn.jsdelivr.net/gh/chaosl1996/ha-share@main/docs/donate.png" alt="微信 / 支付宝赞赏码" width="240">
</p>

> 你的每一份支持，都是我继续维护开源项目的动力 ❤️
<!-- DONATE:END -->
