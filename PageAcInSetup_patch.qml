/* Eastron settings */
	MbItemOptions {
			description: qsTr("Phase")
			bind: Utils.path(root.bindPrefix, "/Phase")
			show: productId == 0xb023 && valid
			possibleValues: [
				MbOption { description: "L1"; value: 0 },
				MbOption { description: "L2"; value: 1 },
				MbOption { description: "L3"; value: 2 }
			]
		}
	MbSpinBox {
		description: qsTr("Refresh Rate")
		show: productId == 0xb023 && item.valid
		item {
			bind: Utils.path(root.bindPrefix, "/RefreshRate")
			unit: "Hz"
			decimals: 0
			step: 1
			max: 10
			min: 1
		}
	}
/* Eastron settings end */