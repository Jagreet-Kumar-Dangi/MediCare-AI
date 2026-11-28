import 'package:material_ui/material_ui.dart';

import '../theme/app_theme.dart';

class BrandMark extends StatelessWidget {
  const BrandMark({super.key, this.size = 52});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: AppTheme.teal,
        borderRadius: BorderRadius.circular(size * 0.3),
      ),
      child: Icon(
        Icons.medical_services_rounded,
        size: size * 0.56,
        color: Colors.white,
        semanticLabel: 'MediCare AI',
      ),
    );
  }
}
