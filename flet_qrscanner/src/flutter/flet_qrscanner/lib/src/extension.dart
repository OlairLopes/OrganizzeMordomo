import 'package:flet/flet.dart';
import 'package:flutter/widgets.dart';

import 'flet_qrscanner.dart';

class Extension extends FletExtension {
  @override
  Widget? createWidget(Key? key, Control control) {
    switch (control.type) {
      case "FletQrscanner":
        return FletQrscannerControl(control: control);
      default:
        return null;
    }
  }
}
