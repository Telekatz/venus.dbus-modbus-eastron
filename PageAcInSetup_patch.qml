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
	MbItemOptions {
		show: productId == 0xb023 && item.valid
		description: qsTr("Energy Counter Source")
		bind: Utils.path(root.bindPrefix, "/EnergyCounter")
		readonly: false
		editable: true
		possibleValues:[
			MbOption{description: qsTr("Device Value"); value: 0 },
			MbOption{description: qsTr("Balancing"); value: 1 },
			MbOption{description: qsTr("Import - Export"); value: 2 }
		]
	}
/* Eastron settings end */