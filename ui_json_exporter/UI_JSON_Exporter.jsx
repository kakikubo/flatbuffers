var global = {
	doc : null,
	delimiter : '/',//レイヤー名から名前、クラス名、ファイル名を切り分けるときの区切り文字。
	resoScale : 1,//解像度。PSD上でのサイズと座標にかけたものをJSON出力。
	fontScale : 1,//1.6857,
	logging : false,//デバッグ用ログをテキストに出力するかどうか。
	flatMode : true,//親子関係で階層を持たせず、すべてrootの直下に置くモード。
	vars : {
		flatZSeq : 0,//flatMode時に使うzのシーケンス
		logText : '',
		errors : [],
		tagUsed : [],
	},
	tree : {},
	stringTable: [],
	tagsTable: [],
	classTable: [],
	commonAssetMode: false,
	commonAssetFileName: "",
	extended:''//拡張子（psd or psb）
}

function log(str){
	global.vars.logText += str + '\r\n';
}

/* -------------------------------------------------------------------------------------------------------- */
//Main Process
(function(){

	if(activeDocument.name.indexOf('psd') > 0){
		global.extended = ".psd";
	}else if(activeDocument.name.indexOf('psb') > 0){
		global.extended = ".psb";
	}

	if(!activeDocument.saved){
		if(confirm('ドキュメントが保存されていません。保存してから実行しますか？')){
			activeDocument.save();
		}else{
			if(!confirm('保存せずに実行しますか？')){
				return;
			}
		}
	}

	if(activeDocument.resolution != 72){
		if(!confirm('ドキュメントの解像度が 72 dpiではありません。\r\n（' + activeDocument.resolution + ' dpiになっています）\r\n一部要素のサイズに影響があるので 72 dpiに変更してから実行することをお勧めします。\r\n変更しなくても自動計算しますので、実行はできます。\r\n実行しますか？')){
			alert("中断しました。");
			return
		}
	}

	global.doc = activeDocument;

	var folderName = activeDocument.name.split(global.extended).join('');
    var folderPath = '/Users/kaname.hidaka/Desktop/KMS/LayoutExporter/OutPut' + '/' + folderName;

	var texturesFolder = new Folder(folderPath);
	var folderSuccess = texturesFolder.create();
	if(!folderSuccess){
		alert('フォルダ生成に失敗しました。終了します。');
		return;
	}

	// common_で始まるPSDの場合、共通素材
	if (folderName.toLowerCase().indexOf('common_') == 0) {
		global.commonAssetMode = true;
	}

	//texturesFolder内の.pngファイルを削除
	var textureFileList = texturesFolder.getFiles('*.png');
	for(var i=0; i<textureFileList.length; i++){
		textureFileList[i].remove();
	}

	var textFile = new File(folderPath + '/' + folderName + '.json');
	textFile.encoding = 'UTF-8';
	if(textFile.exists) textFile.remove();
	var fileSuccess = textFile.open('w');
	if(!fileSuccess){
		alert('ファイルを開けませんでした。終了します。');
		return;
	}

	var canvasWidth = activeDocument.width.value;
	var canvasHeight = activeDocument.height.value;

	global.tree.root = {};
	global.tree.root.class = 'Node';
	global.tree.root.tag = 0;
	global.vars.tagUsed[global.tree.root.tag] = true;
	global.tree.root.z = 0;
	global.vars.flatZSeq++;
	global.tree.root.opacity = 255;
	global.tree.root.anchor_point = {x:0, y:0};
	global.tree.root.position = {x:0, y:0};
	global.tree.root.size = {width:canvasWidth, height:canvasHeight};
	global.tree.root.directory = activeDocument.name.toLowerCase().split(global.extended).join('');
	global.tree.root.childs = [];

	//レイヤー情報をglobal.tree（のchilds）に格納
	checkLayers(activeDocument, global.tree.root, folderPath, {x:global.tree.root.position.x, y:global.tree.root.position.y});

	textFile.write(toJSON(global.tree));

	if(global.logging) textFile.write('\r\n\r\n/*--- Log ---\r\n' + global.vars.logText + '\r\n*/');

	textFile.close();

	// StringTable出力
	var stringTableData = "";
	for (var i=0; i<global.stringTable.length; i++) {
		stringTableData += global.stringTable[i] + "\r\n";
	}
	saveToFile(folderPath + '/stringtable.txt', stringTableData);

	//タグコードを自動で吐き出したい
	var tagsTableData = "";
	for (var i=0; i<global.tagsTable.length; i++) {
		tagsTableData += global.tagsTable[i] + "\r\n";
	}
	tagsTableData += "\r\n\r\n";
	for (var i=0; i<global.classTable.length; i++) {
		tagsTableData += global.classTable[i] + "\r\n";
	}
	saveToFile(folderPath + '/tags.txt', tagsTableData);

	//エラー出力処理
	var errorTextFileName = '_errors_' + activeDocument.name.split(global.extended).join('') + '.txt';
	var errorTextFile = new File(folderPath + '/' + errorTextFileName);
	if(global.vars.errors.length > 0){
		if(errorTextFile.open('w')){
			errorTextFile.encoding = 'UTF-8';
			for(var i=0; i<global.vars.errors.length; i++){
				errorTextFile.write(global.vars.errors[i].layerName + ' : ' + global.vars.errors[i].description + '\r\n');
			}
			errorTextFile.close();
			alert(global.vars.errors.length + '件のエラーが発生しました。"' + errorTextFileName + '"をご確認ください。');
		}else{
			alert(global.vars.errors.length + '件のエラーが発生しましたがテキストファイルに出力することができませんでした。');
		}
	}else{
		if(errorTextFile.exists) errorTextFile.remove();
	}

	//activeDocument.close(SaveOptions.DONOTSAVECHANGES);

	alert('Finished!');
})();

/**
 * 指定したファイルに文字列を書き出す
 * @param {String} filepath	出力先のファイルパス
 * @param {String} data		出力する文字列
 */
function saveToFile(filepath, data){
	var textFile = new File(filepath);
	textFile.encoding = 'UTF-8';
	if(textFile.exists) textFile.remove();
	var fileSuccess = textFile.open('w');
	if(!fileSuccess){
		alert('ファイルを開けませんでした。終了します。');
		return;
	}

	textFile.write(data);

	if(global.logging) textFile.write('\r\n\r\n/*--- Log ---\r\n' + global.vars.logText + '\r\n*/');

	textFile.close();
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 *　レイヤーを走査し、オブジェクトに情報を格納する。
 *　@param	{LayerSet}	parentLayer	対象のレイヤーコレクションの親レイヤーセット
 *　@param	{Object}	parent		親の情報を格納するオブジェクトへの参照
 * @param	{String}	folderPath	画像を格納するフォルダのパス
 *　@param	{Object}	parentPos	親の座標x,yを持つオブジェクト
 */
function checkLayers(parentLayer, parent, folderPath, parentPos){
	var obj = null;
	var zSeq = 0;
	var layers = parentLayer.layers;
	var len = layers.length;
	if(global.flatMode) parentPos.x = parentPos.y = 0;
	layerLoop://switch内でのcontinue用ラベル
	for(var i=len-1; i>=0; i--){
		obj = {};
		var currentLayer = layers[i];
		activeDocument.activeLayer = currentLayer;

		//以下の条件のいずれかに当てはまる場合、JSONに出力しないためスキップする
		//-レイヤーグループでない且つテキストレイヤーでない（ArtLayerの場合はテキストのみJSON出力）
		//-レイヤー名の末尾が「.image」である（レイヤーグループであっても名前の末尾が「.image」であればJSON出力しない）
		//-ボタンのイメージレイヤー（.noemal/.selected/.highlighted/.disabled）である
		if(
			(currentLayer.typename != 'LayerSet' && currentLayer.kind != LayerKind.TEXT)
			|| /\.image\s*$/.test(currentLayer.name)
			|| isButtonImageLayer(currentLayer)
		){
			//log(currentLayer.name + 'はスキップ');
			continue;
		}
		//log(currentLayer.name + '[' + currentLayer.typename + ']');

		var tmpArr = currentLayer.name.split(global.delimiter);
		var tagNumberPart = tmpArr[0];
		var layerNamePart = tmpArr[1];
		var classNamePart = tmpArr[2];
		var fileNamePart = tmpArr[3];

		global.commonAssetFileName = tmpArr[4];

		var fileName = '';
		if(fileNamePart){
			fileName = fileNamePart;
		}else{
			// fileName = activeDocument.name.toLowerCase().split(global.extended).join('') + '_' + String(tagNumberPart);
			fileName = String(tagNumberPart);
		}

		var className = null;
		var textItem = null;//テキストの場合、TextItemを格納する
		//テキストの場合、中身の文字列がレイヤー名になる。
		//文字列に「/」が入っている場合、それが区切り文字としてtmpArr[2]に値が入る場合があるので、LayerKindを見てスキップする必要がある。


		if(classNamePart && currentLayer.kind != LayerKind.TEXT){
			//レイヤー名でClassが指定されている場合
			switch(classNamePart.toLowerCase()){
				case 'node':
					className = 'Node';
					break;
				case 'layout':
					className = 'Layout';
					break;
				case 'sprite':
					className = 'Sprite';
					break;
				case 'scale9sprite':
					className = 'Scale9Sprite';
					break;
				//case 'label':
				//case 'labelttf':
				//	className = 'LabelTTF';
				//	break;
				case 'bmf':
				case 'labelbmfont':
					className = 'LabelBMFont';
					break;
				case 'button':
				case 'controlbutton':
					className = 'ControlButton';
					break;
				case 'switch':
				case 'controlswitch':
					className = 'ControlSwitch';
					break;
				case 'scroll':
				case 'scrollview':
					className = 'ScrollView';
					break;
				case 'input':
				case 'editbox':
					className = 'EditBox';
					break;
				case 'progressbar':
					className = 'ProgressBar';
					break;
				case 'horizontalscroll':
				case 'horizontalscrollview':
				    className = 'CyclicHorizontalScroll';
				    break;
				case 'checkbox':
					className = 'CheckBox';
					break;

				//KMS専用
				case 'button_l_pos':
					className = 'ButtonLargePositive';
					break;
				case 'button_l_neg':
					className = 'ButtonLargeNegative';
					break;
				case 'button_l_chg':
					className = 'ButtonLargeCharges';
					break;
				case 'button_m_pos':
					className = 'ButtonMediumPositive';
					break;
				case 'button_m_neg':
					className = 'ButtonMediumNegative';
					break;
				case 'button_m_chg':
					className = 'ButtonMediumCharges';
					break;
				case 'button_s_pos':
					className = 'ButtonSmallPositive';
					break;
				case 'button_s_neg':
					className = 'ButtonSmallNegative';
					break;
				case 'button_s_chg':
					className = 'ButtonSmallCharges';
					break;
				case 'button_ss_neg':
					className = 'ButtonSSmallNegative';
					break;
				case 'button_back':
					className = 'ButtonBack';
					break;
				case 'button_close':
					className = 'ButtonClose';
					break;
				case 'button_pager':
					className = 'ButtonPager';
					break;

				//画像書き出しのみ
				case 'imageonly':
					obj.image = fileName + '.png';
					var imageLayer = getImageLayer(currentLayer);
					if(imageLayer){
						bounds = exportImage(imageLayer, fileName + '.png', folderPath);
						//ロード用のコード吐き出し。
						var llClass = "imageOnly:" + fileName + '.png';
						global.classTable.push(llClass);

					}else{
						//imageレイヤーが無い場合
						catchError(currentLayer.name, 'imageOnlyに指定されていますが、配下に.imageレイヤーがありませんでした。');
						continue layerLoop;
					}
					break;
				default:
					//上記以外、該当しないものはエラーとする
					catchError(currentLayer.name, 'Class名が正しく設定されていない可能性があります。');
					continue layerLoop;
					break;
			}

		}else{
			//レイヤー名でClassが指定されていない場合
			if(currentLayer.kind == LayerKind.TEXT){
				switch(parent.class){
					case 'ControlButton':
					case 'LabelBMFont':
					case 'CommonButton':
						//親がControlButton, LabelBMFontの場合はテキストレイヤーはボタンのラベルテキストとして扱うためスキップ
						continue layerLoop;
						break;
					default:
						className = 'LabelTTF';
						break;
				}
			}
		}

		if(className){
			//classNameがセットされている場合＝ただのレイヤーでない場合

			//tag設定
			if(!/^\d+$/.test(tagNumberPart)){
				//tag番号が指定されていない場合
				//alert(tagNumberPart  + " / " + className + " / " + classNamePart);
				catchError(currentLayer.name, 'レイヤー名で「tag番号」が指定されていません。');
				continue layerLoop;
			}else if(Number(tagNumberPart) == 0){
				catchError(currentLayer.name, 'tag番号に 0 が指定されています。1以上で指定してください。');
				continue layerLoop;
			}else if(global.vars.tagUsed[Number(tagNumberPart)] == true){
				//既に使用されているtag番号を指定している場合
				catchError(currentLayer.name, 'tag番号 ' + tagNumberPart + ' は他のレイヤーと重複しています。');
				continue layerLoop;
			}
			obj.tag = Number(tagNumberPart);
			global.vars.tagUsed[obj.tag] = true;

			//オブジェクトプロパティ設定
			obj.name = layerNamePart;
			obj.class = className;
			if(global.flatMode){
				obj.z = global.vars.flatZSeq++;
			}else{
				obj.z = zSeq++;
			}
			obj.opacity = currentLayer.opacity * (255 / 100);
			obj.anchor_point = {
				x : 0,
				y : 0
			};
			obj.ll = "LL_NODE";
			obj.llClass = "cocos2d::Node";


			var bounds = {};
			switch(obj.class){
				case 'Node':
					var areaImage = getLayer(currentLayer, /\.area\s*$/);
					if (areaImage) {
						obj.position = {
							x : areaImage.bounds[0].value,
							y : activeDocument.height.value - areaImage.bounds[3].value
						};
						obj.size = {
							width : areaImage.bounds[2].value - areaImage.bounds[0].value,
							height : areaImage.bounds[3].value - areaImage.bounds[1].value
						};
						obj.ll = "LL_NODE";
						obj.llClass = "cocos2d::Node";
					} else{
						catchError(currentLayer.name, 'Nodeに指定されていますが、配下に.areaレイヤーがありませんでした。');
						continue layerLoop;
					}
					break;
				case 'Layout':
					var areaImage = getLayer(currentLayer, /\.area\s*$/);
					if (areaImage) {
						obj.position = {
							x : areaImage.bounds[0].value,
							y : activeDocument.height.value - areaImage.bounds[3].value
						};
						obj.size = {
							width : areaImage.bounds[2].value - areaImage.bounds[0].value,
							height : areaImage.bounds[3].value - areaImage.bounds[1].value
						};
						obj.ll = "LL_LAYOUT";
						obj.llClass = "cocos2d::ui::Layout";
					} else{
						catchError(currentLayer.name, 'Layoutに指定されていますが、配下に.areaレイヤーがありませんでした。');
						continue layerLoop;
					}
					break;
				case 'Scale9Sprite':
					obj.image = fileName + '.png';
					var imageLayer = getImageLayer(currentLayer);
					if(imageLayer){
						//.imageレイヤーが1枚のArtLayerの場合は、そのレイヤーのopacityをobj.opacityにセット。
						//if(imageLayer.typename == 'ArtLayer'){
							obj.opacity = imageLayer.opacity * (255 / 100);
						//}
						bounds = exportImage(imageLayer, fileName + '.png', folderPath);
						obj.size = {
							width : bounds.w,
							height : bounds.h
						};
						obj.position = {
							x : bounds.x - parentPos.x,
							y : bounds.y - parentPos.y
						};

						var capInsetsLayer = getLayer(currentLayer, /\.cap\s*$/);
						if(capInsetsLayer){
							//x, yは左上から（.imageの画像の左上から）
							obj.cap_insets = {
								x : capInsetsLayer.bounds[0].value - imageLayer.bounds[0].value,
								y : capInsetsLayer.bounds[1].value - imageLayer.bounds[1].value,
								//x : capInsetsLayer.bounds[0].value - (obj.position.x - bounds.w * 0.5),
								//y : capInsetsLayer.bounds[1].value - (activeDocument.height.value - (obj.position.y - bounds.h * 0.5) - obj.size.height),
								width : capInsetsLayer.bounds[2].value - capInsetsLayer.bounds[0].value,
								height : capInsetsLayer.bounds[3].value - capInsetsLayer.bounds[1].value
							}
						}else {
							// commonじゃない素材の場合、.capがないとエラー
							// common_で始まる素材の場合、共通素材から引っ張ってくるので.capは不要です
							if(obj.image.toLowerCase().indexOf("common_") != 0) {
								catchError(currentLayer.name, 'Scale9Spriteに指定されていますが、.capレイヤーがありませんでした。');
								continue layerLoop;
							}
						}

						// エリアがある場合はサイズをエリアにあわせる
						var areaImage = getLayer(currentLayer, /\.area\s*$/);
						if (areaImage) {
							obj.position = {
								x : areaImage.bounds[0].value,
								y : activeDocument.height.value - areaImage.bounds[3].value
							};
							obj.size = {
								width : areaImage.bounds[2].value - areaImage.bounds[0].value,
								height : areaImage.bounds[3].value - areaImage.bounds[1].value
							};
						}

						obj.ll = "LL_SCARE_9SPRITE";
						obj.llClass = "cocos2d::ui::Scale9Sprite";

					}else{
						//imageレイヤーが無い場合
						catchError(currentLayer.name, 'Spriteに指定されていますが、配下に.imageレイヤーがありませんでした。');
						continue layerLoop;
					}

					break;
				case 'Sprite':
					obj.image = fileName + '.png';
					var imageLayer = getImageLayer(currentLayer);
					if(imageLayer){
						//.imageレイヤーが1枚のArtLayerの場合は、そのレイヤーのopacityをobj.opacityにセット。
						//if(imageLayer.typename == 'ArtLayer'){
							obj.opacity = imageLayer.opacity * (255 / 100);
						//}
						bounds = exportImage(imageLayer, fileName + '.png', folderPath, obj);
						obj.size = {
							width : bounds.w,
							height : bounds.h
						};
						obj.position = {
							x : bounds.x - parentPos.x + bounds.w * 0.5,
							y : bounds.y - parentPos.y + bounds.h * 0.5
						};
						obj.anchor_point = {
							x : 0.5,
							y : 0.5
						};

						obj.ll = "LL_SPRITE";
						obj.llClass = "cocos2d::Sprite";

					}else{
						//imageレイヤーが無い場合
						catchError(currentLayer.name, 'Spriteに指定されていますが、配下に.imageレイヤーがありませんでした。');
						continue layerLoop;
					}

					break;
				case 'ProgressBar':
					obj.foreground = fileName + '_foreground.png';
        	var foregroundLayer = getLayer(currentLayer, /\.foreground\s*$/);
					if (foregroundLayer) {
					   	//.foregroundレイヤーが1枚のArtLayerの場合は、そのレイヤーのopacityをobj.opacityにセット。
                                                //if(foregroundLayer.typename == 'ArtLayer'){
                                                        obj.opacity = foregroundLayer.opacity * (255 / 100);
                                                //}
                                                bounds = exportImage(foregroundLayer, fileName + '_foreground.png', folderPath);
                                                obj.size = {
                                                        width : bounds.w,
                                                        height : bounds.h
                                                };
                                                obj.position = {
						        x : bounds.x - parentPos.x + bounds.w * 0.5,
                                                        y : bounds.y - parentPos.y + bounds.h * 0.5
                                                };
                                                obj.anchor_point = {
                                                        x : 0.5,
                                                        y : 0.5
                                                };
						var followLayer = getLayer(currentLayer, /\.follow\s*$/);
						if (followLayer) {
						   	obj.follow = fileName + '_follow.png';
						   	exportImage(followLayer, fileName + '_follow.png', folderPath);
						}
						obj.ll = "LL_PROGRESS_BAR";
						obj.llClass = "LL::ProgressBarNode";
					} else {
					       // forgroundLayerがない
					       catchError(currentLayer.name, 'ProgressBarに指定されていますが、配下に.foregroundレイヤーがありませんでした。');
                                               continue layerLoop;
					}
					break;
				case 'CyclicHorizontalScroll':
				    var pagerLayer = getLayer(currentLayer, /\.pager\s*$/);
				    if (pagerLayer) {
				            obj.pager_size = {
				                width : pagerLayer.bounds[2].value - pagerLayer.bounds[0].value,
				                height : pagerLayer.bounds[3].value - pagerLayer.bounds[1].value
				            };
				            obj.pager_position = {
				                x : pagerLayer.bounds[0].value + (pagerLayer.bounds[2].value - pagerLayer.bounds[0].value) / 2,
				                y : activeDocument.height.value - pagerLayer.bounds[3].value + (pagerLayer.bounds[3].value - pagerLayer.bounds[1].value) / 2
				            };
				    }
				    var horizontalScrollLayer = getLayer(currentLayer, /\.visiblesize\s*$/);
				    if (horizontalScrollLayer) {
				            obj.size = {
				                width : horizontalScrollLayer.bounds[2].value - horizontalScrollLayer.bounds[0].value,
				                height : horizontalScrollLayer.bounds[3].value - horizontalScrollLayer.bounds[1].value
				            };
				            obj.position = {
				                x : horizontalScrollLayer.bounds[0].value,
				                y : activeDocument.height.value - horizontalScrollLayer.bounds[3].value
				            };
				            obj.anchor_point = {
				                x : 0.0,
				                y : 0.0
				            };

				            obj.ll = "LL_HORIZONTAL_SCROLL_VIEW(LL_HORIZONTAL_SCROLL_VIEW_PAGER)";
				            obj.llClass = "LL::CyclicHorizontalScroll(LL::PagerNode)";
				    } else {
				            catchError(currentLayer.name, 'HorizontalScrollに指定されていますが、配下に.visiblesizeレイヤーがありませんでした。');
				            continue layerLoop;
				    }
				    break;
				case 'LabelTTF':
				case 'LabelBMFont':
					if(obj.class == 'LabelTTF'){
						textItem = currentLayer.textItem;
						//font_sizeとLabelTTFだけに設定
						obj.font = textItem.font;
						obj.ll = "LL_LABEL";
						obj.llClass = "cocos2d::ui::Text";
					}else if(obj.class == 'LabelBMFont'){
						textItem = getTextItemFromChilds(currentLayer);
						//font名
						if(fileNamePart){
							obj.font = getLayerFileName(currentLayer);
							obj.ll = "LL_LABEL_BMF";
							obj.llClass = "cocos2d::Label";
						}else{
							catchError(currentLayer.name, 'LabelBMFontにフォント名が指定されていません。');
							continue layerLoop;
						}
					}
					obj.color = getColorToObject(textItem);
					obj.font_size = textItem.size.as("px") * global.resoScale * global.fontScale;//フォントサイズに解像度適用。font_sizeはpxに変換すると解像度の影響は受けないので(activeDocument.resolution / 72)はかけない
					obj.text = textItem.contents.split('\r').join('\\n');
					obj.opacity = currentLayer.opacity * (255 / 100);

					// LabelBMFontはstring tableにも吐き出す
					if (obj.class == 'LabelBMFont') {
						var stringTableId = activeDocument.name.split(global.extended).join('') + "." + obj.tag;
						global.stringTable.push(stringTableId + ' ' + obj.font + ' "' + obj.text + '"');
					}

					//水平アライン
					var horizontalAlignment;
					var anchorX = 0.0;
					var anchorY = 1.0;//テキストのanchorは1固定かも？下に文章が増えるから？
					//段落テキストの場合はテキストの設定を、
					if(textItem.kind == TextType.PARAGRAPHTEXT){

						var positionX = textItem.position[0].value;
						var positionY = activeDocument.height.as("px") - (textItem.position[1].value/* + 0.5 * (textItem.height.as("px") * (activeDocument.resolution / 72))*/);

						try{
							if(textItem.justification == Justification.CENTER || textItem.justification == Justification.CENTERJUSTIFIED){
								horizontalAlignment = 'center';
								anchorX = 0.5;
								positionX += 0.5 * (textItem.width.as("px") * (activeDocument.resolution / 72));
							}else if(textItem.justification == Justification.RIGHT || textItem.justification == Justification.RIGHTJUSTIFIED){
								horizontalAlignment = 'right';
								anchorX = 1.0;
								positionX += 1.0 * textItem.width.as("px") * (activeDocument.resolution / 72);
							}else{
								horizontalAlignment = 'left';
								anchorX = 0.0;
							}
						}catch(e){
							horizontalAlignment = 'left';
							anchorX = 0.0;
						}

						//段落テキストの場合はその領域をテキストのサイズとする
						// 横幅が小さすぎるとcocos2dxでは表示できないので注意
						if (textItem.width.as("px") * (activeDocument.resolution / 72) < 40) {
							catchError(currentLayer.name, '横幅が小さすぎます');
							continue layerLoop;
						}

						//Photoshopの環境設定で文字の単位がpointだとtextItem.width/heightがpointの数値を返すため、pxに変換する
						//ただし、PSDの解像度が72dpiでないと正しい数値に変換されないので注意
						obj.dimension = {
							width:textItem.width.as("px")/* * (activeDocument.resolution / 72)*/,
							height:textItem.height.as("px")/* * (activeDocument.resolution / 72)*/
						}

						//段落テキストの場合は、アンカーポイントも指定
						obj.anchor_point = {
							x:anchorX,
							y:anchorY
						}

						// 段落テキストの場合は、位置も調整します
						obj.position = {
							x : positionX,
							y : positionY
						};

						var valign = 'top';//垂直アラインはデフォルトでmiddleとする
						obj.alignment = {
							horizontal : horizontalAlignment,
							vertical : valign
						}
						activeDocument.selection.deselect();

					} else {
						// ポイントテキストはサポートしません
						catchError(currentLayer.name, 'ポイントテキストはサポートされていません。');
						continue layerLoop;
					}

					break;
				case 'ControlButton':
					obj.image = {};
					obj.text = {};
					obj.font_size = {};
					obj.color = {};
					bounds = setButtonImages(currentLayer, fileName, folderPath, obj);
					if(bounds){
						obj.size = {
							width : bounds.w,
							height : bounds.h
						};
						obj.position = {
							x : bounds.x - parentPos.x + bounds.w * 0.5,
							y : bounds.y - parentPos.y + bounds.h * 0.5
						};
						obj.anchor_point = {
							x: 0.5,
							y: 0.5
						};
						obj.ll = "LL_BUTTON";
						obj.llClass = "cocos2d::ui::Button";
					}else{
						//boundsがfalse = ボタンイメージのレイヤーが無い場合
						catchError(currentLayer.name, 'ControlButtonに指定されていますが、配下に.normal, .selected, .highlighted, .disabled のいずれかのレイヤーがありませんでした。');
						continue layerLoop;
					}
					break;

				case 'ButtonLargePositive':
				case 'ButtonLargeNegative':
				case 'ButtonLargeCharges':
				case 'ButtonMediumPositive':
				case 'ButtonMediumNegative':
				case 'ButtonMediumCharges':
				case 'ButtonSmallPositive':
				case 'ButtonSmallNegative':
				case 'ButtonSmallCharges':
				case 'ButtonSSmallNegative':
					var textLayer = getTextItemFromChilds(currentLayer);
					// obj.text = {};
					if(textLayer){
						obj.text = textLayer.contents.split('\r').join('\\n');

						var stringTableId = activeDocument.name.split(global.extended).join('') + "." + obj.tag;

						// KMS仕様。ボタンは２つのフォントを重ねて表示している
						global.stringTable.push(stringTableId + ' emphasis_gradient "' + obj.text + '"');
						global.stringTable.push(stringTableId + ' emphasis_shadow "' + obj.text + '"');
						global.stringTable.push(stringTableId + ' emphasis "' + obj.text + '"');
					}

					var areaImage = getLayer(currentLayer, /\.area\s*$/);
					if (areaImage) {
						obj.position = {
							x : areaImage.bounds[0].value,
							y : activeDocument.height.value - areaImage.bounds[3].value
						};
						obj.size = {
							width : areaImage.bounds[2].value - areaImage.bounds[0].value,
							height : areaImage.bounds[3].value - areaImage.bounds[1].value
						};
						obj.ll = "LL_COMMON_BUTTON";
						obj.llClass = "kms::CommonButton";
					} else{
						catchError(currentLayer.name, 'Layoutに指定されていますが、配下に.areaレイヤーがありませんでした。');
						continue layerLoop;
					}
					obj.type = {};
					switch(obj.class){
						case 'ButtonLargePositive':
							obj.type.size = "Large";
							obj.type.design = "Positive"
							break;
						case 'ButtonLargeNegative':
							obj.type.size = "Large";
							obj.type.design = "Negative"
							break;
						case 'ButtonLargeCharges':
							obj.type.size = "Large";
							obj.type = "Charges";
							break;
						case 'ButtonMediumPositive':
							obj.type.size = "Medium";
							obj.type.design = "Positive"
							break;
						case 'ButtonMediumNegative':
							obj.type.size = "Medium";
							obj.type.design = "Negative"
							break;
						case 'ButtonMediumCharges':
							obj.type.size = "Medium";
							obj.type = "Charges";
							break;
						case 'ButtonSmallPositive':
							obj.type.size = "Small";
							obj.type.design = "Positive"
							break;
						case 'ButtonSmallNegative':
							obj.type.size = "Small";
							obj.type.design = "Negative"
							break;
						case 'ButtonSmallCharges':
							obj.type.size = "Small";
							obj.type = "Charges";
							break;
						case 'ButtonSSmallNegative':
							obj.type.size = "SSmall";
							obj.type.design = "Negative"
							break;
					}
					obj.class = "CommonButton"

					break;
				case 'ButtonBack':
				case 'ButtonClose':
				case 'ButtonPager':

					var textLayer = getTextItemFromChilds(currentLayer);
					// obj.text = {};
					if(textLayer){
						obj.text = textLayer.contents.split('\r').join('\\n');

						var stringTableId = activeDocument.name.split(global.extended).join('') + "." + obj.tag;
						global.stringTable.push(stringTableId + ' ' + obj.font + ' "' + obj.text + '"');
					}
					var areaImage = getLayer(currentLayer, /\.area\s*$/);
					if (areaImage) {
						obj.position = {
							x : areaImage.bounds[0].value,
							y : activeDocument.height.value - areaImage.bounds[3].value
						};
						obj.ll = "LL_COMMON_BUTTON";
						obj.llClass = "kms::CommonButton";
					} else {
						catchError(currentLayer.name, 'Button系に指定されていますが、配下に.areaレイヤーがありませんでした。');
						continue layerLoop;
					}
					obj.type = {};

					switch(obj.class){
						case 'ButtonBack':
							obj.type.design = "Back"
						break;
						case 'ButtonClose':
							obj.type.design = "Close"
						break;
						case 'ButtonPager':
							obj.type.design = "Pager"
						break;
					}

					obj.type.size = "Small"
					obj.class = "CommonButton"

					break;
				case 'ScrollView':
					var scrollAreaImage = getLayer(currentLayer, /\.area\s*$/);
					if(scrollAreaImage){
						obj.size = {
							width : scrollAreaImage.bounds[2].value - scrollAreaImage.bounds[0].value,
							height : scrollAreaImage.bounds[3].value - scrollAreaImage.bounds[1].value
						};
						obj.position = {
							x : scrollAreaImage.bounds[0].value,
							y : activeDocument.height.value - scrollAreaImage.bounds[3].value
						};
						//obj.padding_opacity = 0;
						//obj.padding_color = 0;
						obj.opacity = 0;
						//obj.color = 0;
						obj.ll = "LL_SCROLL_VIEW(LL_SCROLL_BAR)";
						obj.llClass = "SelectiveScroll(LL::VerticalScrollBar)";
					}else{
						catchError(currentLayer.name, 'ScrollViewに指定されていますが、配下に.areaレイヤーがありませんでした。');
						continue layerLoop;
					}

					var scrollBarImage = getLayer(currentLayer, /\.bar\s*$/);
					if(scrollBarImage){
						obj.bar_size = {
							width : scrollBarImage.bounds[2].value - scrollBarImage.bounds[0].value,
							height : scrollBarImage.bounds[3].value - scrollBarImage.bounds[1].value
						};
						// バーの位置は、スクロールビュー自体の位置からの差分です
						obj.bar_position = {
							x : scrollBarImage.bounds[0].value - obj.position.x,
							y : activeDocument.height.value - scrollBarImage.bounds[3].value - obj.position.y
						};
					}

					break;
				case 'EditBox':
					obj.image = {};
					obj.text = {};
					obj.font_size = {};
					obj.color = {};
					bounds = setButtonImages(currentLayer, fileName, folderPath, obj);

					obj.font_color =
					obj.placeholder_font_color = obj.color.normal;
					obj.text = '';

					if(bounds){
						obj.size = {
							width : bounds.w,
							height : bounds.h
						};
						obj.position = {
							x : bounds.x - parentPos.x,
							y : bounds.y - parentPos.y
						};
						obj.ll = "LL_EDIT_BOX";
						obj.llClass = "cocos2d::ui::EditBox";
					}else{
						//boundsがfalse = 背景イメージのレイヤーが無い場合
						catchError(currentLayer.name, 'EditBoxに指定されていますが、配下に.normal, .selected, .highlighted, .disabled のいずれかのレイヤーがありませんでした。');
						continue layerLoop;
					}
					break;
				case 'CheckBox':
					obj.image = {};
					obj.text = {};
					obj.font_size = {};
					obj.color = {};
					bounds = setButtonImages(currentLayer, fileName, folderPath, obj);

					if(bounds){
						obj.size = {
							width : bounds.w,
							height : bounds.h
						};
						obj.position = {
							x : bounds.x - parentPos.x + bounds.w * 0.5,
							y : bounds.y - parentPos.y + bounds.h * 0.5
						};
						obj.anchor_point = {
							x: 0.5,
							y: 0.5
						};
						obj.ll = "LL_CHECK_BOX";
						obj.llClass = "cocos2d::ui::CheckBox";
					}else{
						//boundsがfalse = ボタンイメージのレイヤーが無い場合
						catchError(currentLayer.name, 'ControlButtonに指定されていますが、配下に.normal, .selected, .highlighted, .disabled のいずれかのレイヤーがありませんでした。');
						continue layerLoop;
					}
					break;
				default:
					break;
			}

			//ロード用のコード吐き出し。
			var llCode = obj.name+" = "+obj.ll+"(nodes, "+obj.tag+");";
			global.tagsTable.push(llCode);
			var llClass = obj.llClass+"* "+obj.name+" = nullptr;";
			global.classTable.push(llClass);

			//parent position
			var pp = {
				x : parentPos.x + obj.position.x,
				y : parentPos.y + obj.position.y
			};

			if(obj.size){
				//解像度適用
				obj.size.width *= global.resoScale;
				obj.size.height *= global.resoScale;
			}
			if(obj.position){
				//解像度適用
				obj.position.x *= global.resoScale;
				obj.position.y *= global.resoScale;
			}

			if(global.flatMode){
				global.tree.root.childs.push(obj);
			}else{
				parent.childs.push(obj);
			}
		}else{
			//ただのレイヤーの場合
			obj.class = null;
		}

		if(currentLayer.typename == 'LayerSet'){
			if(obj.class){
				//クラスがある場合
				obj.childs = [];
				checkLayers(currentLayer, obj, folderPath, pp);
			}else{
				//ただのレイヤーの場合は、自身の親を子の親とする
				checkLayers(currentLayer, parent, folderPath, {x:parentPos.x, y:parentPos.y});
			}
		}

	}//for
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * レイヤーの名前からクラス名を抜き出して返す。
 * @param	{ArtLayer|LayerSet}	layer	対象レイヤー
 * @returns	{*}		クラス名がセットされていればその文字列、無ければfalse
 */
function getLayerClassName(layer){
	var className = getPartOfLayerName(layer, 2);
	if(className){
		return className;
	}else{
		return false;
	}
}

function getLayerFileName(layer){
	var name = getPartOfLayerName(layer, 3);
	if(name){
		return name;
	}else{
		return false;
	}
}

function getPartOfLayerName(layer, index){
	return layer.name.split(global.delimiter)[index];
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * 子レイヤーの中から「.image」で終わる名前のレイヤーを探して返す。
 * @param	{ArtLayer|LayerSet}	layer	対象レイヤー
 * @returns	{*}		「.image」で終わる名前のレイヤーがあればそのLayerインスタンス、無ければfalse
 */
function getImageLayer(layer){
	/*
	if(layer.typename != 'LayerSet'){
		return false;
	}
	var len = layer.layers.length;
	for(var i=0; i<len; i++){
		if(/\.image\s*$/.test(layer.layers[i].name)){
			return layer.layers[i];
		}
	}
	return false;
	*/

	return getLayer(layer ,/\.image\s*$/);
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * 子レイヤーの中からテキストレイヤーを探してそのTextItemを返す。
 * @param	{LayerSet}	layer	対象レイヤーセット
 * @returns	{*}		テキストレイヤーがあればそのレイヤーのTextItemインスタンス、無ければfalse
 */
function getTextItemFromChilds(layer){
	if(layer.typename != 'LayerSet'){
		return false;
	}
	var len = layer.layers.length;
	for(var i=0; i<len; i++){
		if(layer.layers[i].kind == LayerKind.TEXT){
			return layer.layers[i].textItem;
		}
	}
	return false;
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * 子レイヤーの中からパラメータで渡された正規表現にマッチする名前のレイヤーを探して返す。
 * @param	{ArtLayer|LayerSet}	layer	対象レイヤー
 * @returns	{*}		正規表現にマッチする名前のレイヤーがあればそのLayerインスタンス、無ければfalse
 */
function getLayer(layer, re){
	var len = layer.layers.length;
	for(var i=0; i<len; i++){
		if(re.test(layer.layers[i].name)){
			return layer.layers[i];
		}
	}
	return false;
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * 対象レイヤーグループがボタンレイヤーかどうかを返す。
 * ボタンレイヤーかどうかは、レイヤー名の末尾が「.normal」「.selected」「.highlighted」「.disabled」のいずれかに該当するレイヤーを子に持つかどうかで判断する。
 * @param	{ArtLayer|LayerSet}	layer	対象レイヤー
 * @returns	{Boolean}		ボタンのイメージレイヤーかどうか
 */
function hasButtonImageLayer(layer){
	if(layer.typename != 'LayerSet') return false;
	var len = layer.layers.length;
	for(var i=0; i<len; i++){
		if(
			/\.normal\s*$/.test(layer.layers[i].name)
			|| /\.selected\s*$/.test(layer.layers[i].name)
			|| /\.highlighted\s*$/.test(layer.layers[i].name)
			|| /\.disabled\s*$/.test(layer.layers[i].name)
		) return true;
	}
	return false;
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * 対象レイヤーがボタンのイメージレイヤーに該当するかどうかを返す。
 * @param	{ArtLayer|LayerSet}	layer	対象レイヤー
 * @returns	{Boolean}		ボタンのイメージレイヤーかどうか
 */
function isButtonImageLayer(layer){
	return (/\.normal\s*$/.test(layer.name) || /\.selected\s*$/.test(layer.name) || /\.highlighted\s*$/.test(layer.name) || /\.disabled\s*$/.test(layer.name));
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * ボタンとして渡された対象レイヤーのボタン画像を書き出す。
 * ボタン画像は状態ごとにそれぞれレイヤー名の末尾に「.normal」「.selected」「.highlighted」「.disabled」が付くレイヤーを対象とする。
 * @param	{LayerSet}	layer	 	対象レイヤーセット
 * @param	{String}	fileName 	画像ファイルとして保存するときのファイル名（拡張子除く）
 * @param	{String}	folderPath	画像ファイルを保存する場所のパス
 * @param	{Object}	obj			ボタン情報をセットするオブジェクト
 * @returns	{Object}	書き出した画像のキャンバス上での座標と大きさを格納したオブジェクト（座標は左下を原点として、右方向がX、上方向がY）
 */
function setButtonImages(layer, fileName, folderPath, obj){
	//log('●setButtonImages : ' + layer.name + ' -> ' + fileName);
	var len = layer.layers.length;
	var bounds = false;

	//ラベルテキストが無い場合のためデフォルト値をセット
	obj.font_size.normal =
	obj.font_size.selected =
	obj.font_size.highlighted =
	obj.font_size.disabled = 12;
	obj.color.normal =
	obj.color.selected =
	obj.color.highlighted =
	obj.color.disabled = {
		r : 0,
		g : 0,
		b : 0
	}

	for(var i=0; i<len; i++){
		if(/\.normal\s*$/.test(layer.layers[i].name)){
			obj.image.normal = fileName + '.normal.png';
			layer.layers[i].visible = true;
			bounds = exportImage(layer.layers[i], obj.image.normal, folderPath);
			//obj.text.normal = '';
		}else if(/\.selected\s*$/.test(layer.layers[i].name)){
			obj.image.selected = fileName + '.selected.png';
			layer.layers[i].visible = true;
			bounds = exportImage(layer.layers[i], obj.image.selected, folderPath);
			//obj.text.selected = '';
		}else if(/\.highlighted\s*$/.test(layer.layers[i].name)){
			obj.image.highlighted = fileName + '.highlighted.png';
			layer.layers[i].visible = true;
			bounds = exportImage(layer.layers[i], obj.image.highlighted, folderPath);
			//obj.text.highlighted = '';
		}else if(/\.disabled\s*$/.test(layer.layers[i].name)){
			obj.image.disabled = fileName + '.disabled.png';
			layer.layers[i].visible = true;
			bounds = exportImage(layer.layers[i], obj.image.disabled, folderPath);
			//obj.text.disabled = '';
		}else if(/\.effect\s*$/.test(layer.layers[i].name)){
			obj.image.effect = fileName + '.effect.png';
			layer.layers[i].visible = true;
			bounds = exportImage(layer.layers[i], obj.image.effect, folderPath);
			//obj.text.disabled = '';
		}else if(/\.trace\s*$/.test(layer.layers[i].name)){
			obj.image.trace = fileName + '.trace.png';
			layer.layers[i].visible = true;
			bounds = exportImage(layer.layers[i], obj.image.trace, folderPath);
			//obj.text.disabled = '';
		}else if(layer.layers[i].kind == LayerKind.TEXT){
			//ボタンのラベル
			obj.text.normal =
			obj.text.selected =
			obj.text.highlighted =
			obj.text.disabled = layer.layers[i].textItem.contents;
			obj.font_size.normal =
			obj.font_size.selected =
			obj.font_size.highlighted =
			obj.font_size.disabled = layer.layers[i].textItem.size.as("px") * global.resoScale;//font_sizeはpxに変換すると解像度の影響は受けないので(activeDocument.resolution / 72)はかけない
			obj.color.normal =
			obj.color.selected =
			obj.color.highlighted =
			obj.color.disabled = getColorToObject(layer.layers[i].textItem);
		}
	}

	return bounds;
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * スイッチとして渡された対象レイヤーのボタン画像を書き出す。
 * スイッチ画像は状態ごとにそれぞれレイヤー名の末尾に「.mask」「.on」「.off」「.thumb」が付くレイヤーを対象とする。
 * @param	{LayerSet}	layer	 	対象レイヤーセット
 * @param	{String}	fileName 	画像ファイルとして保存するときのファイル名（拡張子除く）
 * @param	{String}	folderPath	画像ファイルを保存する場所のパス
 * @param	{Object}	obj			ボタン情報をセットするオブジェクト
 * @returns	{Object}	書き出した画像のキャンバス上での座標と大きさを格納したオブジェクト（座標は左下を原点として、右方向がX、上方向がY）
 */
function setSwitchImages(layer, fileName, folderPath, obj){
	//log('●setButtonImages : ' + layer.name + ' -> ' + fileName);
	var len = layer.layers.length;
	var bounds = false;

	//ラベルテキストが無い場合のためデフォルト値をセット
	obj.font_size.on =
	obj.font_size.off = 12;
	obj.color.on =
	obj.color.off = {
		r : 0,
		g : 0,
		b : 0
	}

	for(var i=0; i<len; i++){
		if(/\.mask\s*$/.test(layer.layers[i].name)){
			obj.image.mask = fileName + '.mask.png';
			layer.layers[i].visible = true;
			bounds = exportImage(layer.layers[i], obj.image.mask, folderPath);
		}else if(/\.on\s*$/.test(layer.layers[i].name)){
			obj.image.on = fileName + '.on.png';
			layer.layers[i].visible = true;
			exportImage(layer.layers[i], obj.image.on, folderPath);
		}else if(/\.off\s*$/.test(layer.layers[i].name)){
			obj.image.off = fileName + '.off.png';
			layer.layers[i].visible = true;
			exportImage(layer.layers[i], obj.image.off, folderPath);
		}else if(/\.thumb\s*$/.test(layer.layers[i].name)){
			obj.image.thumb = fileName + '.thumb.png';
			layer.layers[i].visible = true;
			exportImage(layer.layers[i], obj.image.thumb, folderPath);
		}else if(layer.layers[i].kind == LayerKind.TEXT){
			//スイッチのラベル
			obj.text.on =
			obj.text.off = layer.layers[i].textItem.contents;
			obj.font_size.on =
			obj.font_size.off = layer.layers[i].textItem.size.value * global.resoScale;
			obj.color.on =
			obj.color.off = getColorToObject(layer.layers[i].textItem);
		}
	}

	return bounds;
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * TextItemのカラーをオブジェクトにセットして返す。
 * カラーがrgb(0,0,0)だとTextItem.colorがセットされていないらしく、アクセスするとエラーになるので
 * 例外処理で対応する。
 * @param	{TextItem}	textItem	対象のTextItem
 * @returns {Object}	obj			プロパティr,g,bにカラー値をセットしたオブジェクト
 */
function getColorToObject(textItem){
	var c = {};
	try{
		c = {
			r : Math.round(textItem.color.rgb.red),
			g : Math.round(textItem.color.rgb.green),
			b : Math.round(textItem.color.rgb.blue)
		};
	}catch(e){
		c = {
			r : 0,
			g : 0,
			b : 0
		};
	}
	return c;
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * レイヤーをPNG画像として書き出す。
 * 対象レイヤーはArtLayerでもLayerSetでもかまわない。
 * @param	{ArtLayer|LayerSet}	layer		対象レイヤー
 * @param	{String}			fileName	ファイル名（拡張子を含む）
 * @param	{String}			path		保存場所のパス
 * @returns	{Object}	書き出した画像のキャンバス上での座標と大きさを格納したオブジェクト（座標は左下を原点として、右方向がX、上方向がY）
 */
function exportImage(layer, fileName, path, obj){

	//log('●exportImage : ' + layer.name + ' -> ' + fileName);
	var b = layer.bounds;
	var x1 = b[0].value;
	var y1 = b[1].value;
	var x2 = b[2].value;
	var y2 = b[3].value;
	var w = x2 - x1;
	var h = y2 - y1;
	var b = {
		x : x1,
		y : activeDocument.height.value - y2,
		w : w,
		h : h
	};

	// PSDがcommon_じゃなくて、画像名が"common_"で始まる場合、共通アイコンなので出力しないでサイズを返す
	if (global.commonAssetMode == false && fileName.toLowerCase().lastIndexOf('common_', 0) === 0) {
		var nameWithOutExt = fileName.split(".");
		var dir = nameWithOutExt[0].split("_");
		var newFileName = "";
		if (global.commonAssetFileName !== "") {
			for (var i = 0; i < dir.length; ++i) {
				newFileName += dir	[i] + "/";
			}
			fileName = newFileName + global.commonAssetFileName + ".png";
			if (obj !== undefined) {
				obj.image = fileName;
			}
		}

		return b;
	}

	var doc = activeDocument;

	//New Document
	preferences.rulerUnits = Units.PIXELS;
	var newDocument = documents.add(w, h, 72, layer.name, NewDocumentMode.RGB, DocumentFill.TRANSPARENT);

	activeDocument = doc;
	var layer2 = layer.duplicate(newDocument);
	activeDocument = newDocument;
	layer2.translate(x1 * -1, y1 * -1);

	var pngName = fileName;
	var saveFile = new File(path + '/' + pngName);
	var opt = new PNGSaveOptions();
	opt.PNG8 = true;
	newDocument.saveAs(saveFile, opt, true, Extension.LOWERCASE);
	newDocument.close(SaveOptions.DONOTSAVECHANGES);

	return b;

}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * 選択レイヤーのレイヤーマスクの範囲を取得して返す。
 * レイヤーマスクが無い場合はドキュメントのキャンバスサイズと同じ範囲が返るので、その場合はレイヤーマスクを持っていないものとみなす。
 * @returns	{*}	レイヤーマスクがあれば座標と大きさ（x, y, width, height）のパラメータを持つオブジェクト、無ければfalse。
 */
function getLayerMask(){
	// Read mask
	var idsetd = charIDToTypeID( "setd" );
	var desc = new ActionDescriptor();
	var idnull = charIDToTypeID( "null" );
	var ref = new ActionReference();
	var idChnl = charIDToTypeID( "Chnl" );
	var idfsel = charIDToTypeID( "fsel" );
	ref.putProperty( idChnl, idfsel );
	desc.putReference( idnull, ref );
	var idT = charIDToTypeID( "T   " );
	var ref = new ActionReference();
	var idChnl = charIDToTypeID( "Chnl" );
	var idOrdn = charIDToTypeID( "Ordn" );
	var idTrgt = charIDToTypeID( "Trgt" );
	ref.putEnumerated( idChnl, idOrdn, idTrgt );
	desc.putReference( idT, ref );
	executeAction( idsetd, desc, DialogModes.NO );

	// Coordinates　Acquisition
	var x1str = activeDocument.selection.bounds[0]; //Upper left X;
	var y1str = activeDocument.selection.bounds[1]; //Upper left Y;
	var x2str = activeDocument.selection.bounds[2]; //Lower right X;
	var y2str = activeDocument.selection.bounds[3]; //Lower right Y;

	if(
		x1str != 0
		&& y1str != 0
		&& x2str - x1str != activeDocument.width
		&& y2str - y1str != activeDocument.height
	){
		//レイヤーマスクがある場合
		return {
			x : x1str.value,
			y : y1str.value,
			width : x2str.value - x1str.value,
			height : y2str.value - y1str.value
		};
	}else{
		//レイヤーマスクが無い場合
		return false;
	}
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * アクティブレイヤーがレイヤーマスクを持っているかどうかを返す。
 * レイヤーマスクの範囲がドキュメントのキャンバスサイズと同じ場合は持っていないものとみなす。
 * @returns	{Boolean}	レイヤーマスクを持っているかどうか。
 */
function getHasLayerMask(){
	var maskRect = getLayerMask();
	var result = false;
	if(maskRect){
		result = (
			maskRect.x != 0
			&& maskRect.y != 0
			&& maskRect.width != activeDocument.width
			&& maskRect.height != activeDocument.height
		);
	}
	activeDocument.selection.deselect();
	return result;
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * エラーをログに蓄積する。
 * @param	{String}	layerName	対象のレイヤー名
 * @param	{String}	description	エラーの内容
 */
function catchError(layerName, description){
	global.vars.errors.push({
		layerName : layerName,
		description : description
	});
}

/* -------------------------------------------------------------------------------------------------------- */
/**
 * オブジェクトをJSON形式にコンバートした文字列を返す。
 * @param	{Object}	obj	対象オブジェクト
 * @returns	{String}	JSON文字列
 */
function toJSON(obj){
	var str = '{\r\n';

	var isFirst = true;
	for(var i in obj){
		if(isFirst){
			isFirst = false;
		}else{
			str += ',\r\n';
		}
		if(i === 'childs'){
			str += '\"' + i + '\":[';
			var isFirstChild = true;
			for(var ii in obj[i]){
				if(isFirstChild){
					isFirstChild = false;
				}else{
					str += ',\r\n';
				}
				str += toJSON(obj[i][ii])
			}
			str += ']';
		}else if(typeof(obj[i]) == 'object'){
			str += '\"' + i + '\":' + toJSON(obj[i]);
		}else if(typeof(obj[i]) == 'number'){
			str += '\"' + i + '\":' + obj[i];
		}else if(typeof(obj[i]) == 'string'){
			str += '\"' + i + '\":\"' + obj[i] + '\"';
		}else{
			//log('どれでもない:' + typeof(obj[i]));
		}
	}

	str += '\r\n}\r\n';

	return str;
}
