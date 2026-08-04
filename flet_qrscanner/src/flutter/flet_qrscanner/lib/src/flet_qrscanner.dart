import 'package:flet/flet.dart';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

class FletQrscannerControl extends StatefulWidget {
  final Control control;

  const FletQrscannerControl({
    super.key,
    required this.control,
  });

  @override
  State<FletQrscannerControl> createState() => _FletQrscannerControlState();
}

class _FletQrscannerControlState extends State<FletQrscannerControl> {
  late MobileScannerController controller;

  @override
  void initState() {
    super.initState();
    controller = MobileScannerController(
      facing: widget.control.getString("camera_facing", "back") == "front"
          ? CameraFacing.front
          : CameraFacing.back,
      torchEnabled: widget.control.getBool("torch_enabled", false)!,
    );
  }

  @override
  void didUpdateWidget(covariant FletQrscannerControl oldWidget) {
    super.didUpdateWidget(oldWidget);
    final torchEnabled = widget.control.getBool("torch_enabled", false)!;
    if (torchEnabled != (controller.value.torchState == TorchState.on)) {
      controller.toggleTorch();
    }
  }

  void _onDetect(BarcodeCapture capture) {
    if (capture.barcodes.isEmpty) {
      return;
    }
    final barcode = capture.barcodes.first;
    widget.control.triggerEvent("detect", {
      "code": barcode.rawValue ?? "",
      "format": barcode.format.name,
    });
  }

  @override
  Widget build(BuildContext context) {
    return LayoutControl(
      control: widget.control,
      child: MobileScanner(
        controller: controller,
        onDetect: _onDetect,
      ),
    );
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }
}
