"use strict";
(self["webpackChunk"] = self["webpackChunk"] || []).push([["./react/pages/admin-ChartFlex-js"],{

/***/ "./resources/simulation/components/admin/ChartFlex/ChartClone.js":
/*!***********************************************************************!*\
  !*** ./resources/simulation/components/admin/ChartFlex/ChartClone.js ***!
  \***********************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-runtime */ "./node_modules/react/jsx-runtime.js");
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! react */ "./node_modules/react/index.js");
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }




function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

function _createSuper(Derived) { var hasNativeReflectConstruct = _isNativeReflectConstruct(); return function _createSuperInternal() { var Super = _getPrototypeOf(Derived), result; if (hasNativeReflectConstruct) { var NewTarget = _getPrototypeOf(this).constructor; result = Reflect.construct(Super, arguments, NewTarget); } else { result = Super.apply(this, arguments); } return _possibleConstructorReturn(this, result); }; }

function _possibleConstructorReturn(self, call) { if (call && (_typeof(call) === "object" || typeof call === "function")) { return call; } else if (call !== void 0) { throw new TypeError("Derived constructors may only return object or undefined"); } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _isNativeReflectConstruct() { if (typeof Reflect === "undefined" || !Reflect.construct) return false; if (Reflect.construct.sham) return false; if (typeof Proxy === "function") return true; try { Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function () {})); return true; } catch (e) { return false; } }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }



var ChartClone = /*#__PURE__*/function (_Component) {
  _inherits(ChartClone, _Component);

  var _super = _createSuper(ChartClone);

  function ChartClone(props) {
    var _this;

    _classCallCheck(this, ChartClone);

    _this = _super.call(this, props);
    _this.id = makeId();
    _this.state = {
      config: ''
    };
    return _this;
  }

  _createClass(ChartClone, [{
    key: "onClickHandle",
    value: function onClickHandle() {
      if (this.props.onApply) {
        this.props.onApply(JSON.parse(this.state.config));
      }
    }
  }, {
    key: "setConfig",
    value: function setConfig(config) {
      config = JSON.stringify(config, null, 2);
      this.setState({
        config: config
      });
    }
  }, {
    key: "modal",
    value: function modal() {
      var cmd = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : 'show';

      if (cmd == 'hide') {
        $("#edit_row_modal" + this.id).modal('hide');
      } else {
        $("#edit_row_modal" + this.id).modal();
      }
    }
  }, {
    key: "setDefault",
    value: function setDefault() {
      if (this.props.onSetDefault) {
        this.props.onSetDefault(JSON.parse(this.state.config));
      }
    }
  }, {
    key: "render",
    value: function render() {
      var _this2 = this;

      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
        className: "modal fade",
        id: "edit_row_modal" + this.id,
        onClick: function onClick() {
          addClass($('body')[0], 'modal-open');
        },
        children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
          className: "modal-dialog modal-lg modal-dialog-centered",
          style: {
            maxWidth: '90%'
          },
          children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
            className: "modal-content",
            children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
              className: "modal-header",
              children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("h4", {
                className: "modal-title",
                children: this.state.title
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("button", {
                type: "button",
                className: "close",
                "data-dismiss": "modal",
                children: "\xD7"
              })]
            }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
              className: "modal-body",
              style: {
                textAlign: 'initial'
              },
              children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("textarea", {
                style: {
                  width: '100%',
                  minHeight: 500
                },
                className: "input",
                value: this.state.config,
                onChange: function onChange(e) {
                  return _this2.setState({
                    config: e.target.value
                  });
                }
              })
            }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
              className: "modal-footer",
              children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("button", {
                type: "button",
                className: "btn btn-primary",
                onClick: function onClick() {
                  _this2.setDefault(_this2.state.config);
                },
                children: lang('Set as Default')
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("button", {
                type: "button",
                className: "btn btn-info",
                onClick: function onClick() {
                  copyToClipboard(_this2.state.config);
                },
                children: lang('Copy')
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("button", {
                type: "button",
                className: "btn btn-warning",
                onClick: function onClick() {
                  _this2.onClickHandle();
                },
                children: lang('Apply')
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("button", {
                type: "button",
                className: "btn btn-danger",
                "data-dismiss": "modal",
                children: lang('Close')
              })]
            })]
          })
        })
      });
    }
  }]);

  return ChartClone;
}(react__WEBPACK_IMPORTED_MODULE_1__.Component);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (ChartClone);

/***/ }),

/***/ "./resources/simulation/components/admin/ChartFlex/ChartConfig.js":
/*!************************************************************************!*\
  !*** ./resources/simulation/components/admin/ChartFlex/ChartConfig.js ***!
  \************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-runtime */ "./node_modules/react/jsx-runtime.js");
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! react */ "./node_modules/react/index.js");
/* harmony import */ var _components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ../../../components/Input_v2/Input */ "./resources/simulation/components/Input_v2/Input.js");
/* harmony import */ var _model_admin_ChartFelxModel__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ../../../model/admin/ChartFelxModel */ "./resources/simulation/model/admin/ChartFelxModel.js");
/* harmony import */ var _common_DragSort__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ../../common/DragSort */ "./resources/simulation/components/common/DragSort.js");
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }




function _createForOfIteratorHelper(o, allowArrayLike) { var it = typeof Symbol !== "undefined" && o[Symbol.iterator] || o["@@iterator"]; if (!it) { if (Array.isArray(o) || (it = _unsupportedIterableToArray(o)) || allowArrayLike && o && typeof o.length === "number") { if (it) o = it; var i = 0; var F = function F() {}; return { s: F, n: function n() { if (i >= o.length) return { done: true }; return { done: false, value: o[i++] }; }, e: function e(_e) { throw _e; }, f: F }; } throw new TypeError("Invalid attempt to iterate non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); } var normalCompletion = true, didErr = false, err; return { s: function s() { it = it.call(o); }, n: function n() { var step = it.next(); normalCompletion = step.done; return step; }, e: function e(_e2) { didErr = true; err = _e2; }, f: function f() { try { if (!normalCompletion && it["return"] != null) it["return"](); } finally { if (didErr) throw err; } } }; }

function _unsupportedIterableToArray(o, minLen) { if (!o) return; if (typeof o === "string") return _arrayLikeToArray(o, minLen); var n = Object.prototype.toString.call(o).slice(8, -1); if (n === "Object" && o.constructor) n = o.constructor.name; if (n === "Map" || n === "Set") return Array.from(o); if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen); }

function _arrayLikeToArray(arr, len) { if (len == null || len > arr.length) len = arr.length; for (var i = 0, arr2 = new Array(len); i < len; i++) { arr2[i] = arr[i]; } return arr2; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

function _createSuper(Derived) { var hasNativeReflectConstruct = _isNativeReflectConstruct(); return function _createSuperInternal() { var Super = _getPrototypeOf(Derived), result; if (hasNativeReflectConstruct) { var NewTarget = _getPrototypeOf(this).constructor; result = Reflect.construct(Super, arguments, NewTarget); } else { result = Super.apply(this, arguments); } return _possibleConstructorReturn(this, result); }; }

function _possibleConstructorReturn(self, call) { if (call && (_typeof(call) === "object" || typeof call === "function")) { return call; } else if (call !== void 0) { throw new TypeError("Derived constructors may only return object or undefined"); } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _isNativeReflectConstruct() { if (typeof Reflect === "undefined" || !Reflect.construct) return false; if (Reflect.construct.sham) return false; if (typeof Proxy === "function") return true; try { Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function () {})); return true; } catch (e) { return false; } }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }






var ChartConfig = /*#__PURE__*/function (_Component) {
  _inherits(ChartConfig, _Component);

  var _super = _createSuper(ChartConfig);

  function ChartConfig(props) {
    var _this;

    _classCallCheck(this, ChartConfig);

    _this = _super.call(this, props);
    _this.id = makeId();
    _this.state = {
      configs: [],
      symbol: '',
      title: '',
      database: '',
      height: 250,
      source_data_options: [],
      symbol_options: [],
      source_field_options: {},
      database_options: [],
      type_options: [{
        'value': '',
        'label': ''
      }, {
        'value': 'line',
        'label': 'Line'
      }, {
        'value': 'bar',
        'label': 'Bar'
      }, {
        'value': 'bar_histogram',
        'label': 'Bar Histogram'
      }, {
        'value': 'candlestick',
        'label': 'Candle Stick'
      }],
      dash_options: [{
        'value': '',
        'label': ''
      }, {
        'value': 'solid',
        'label': 'Solid'
      }, {
        'value': 'dash',
        'label': 'Dash'
      }, {
        'value': 'dot',
        'label': 'Dot'
      }],
      agg_optipons: [{
        'value': '',
        'label': ''
      }, {
        'value': 'sum',
        'label': 'Sum'
      }, {
        'value': 'max',
        'label': 'Max'
      }, {
        'value': 'min',
        'label': 'Min'
      }, {
        'value': 'first',
        'label': 'First'
      }, {
        'value': 'last',
        'label': 'Last'
      }]
    };
    _this.model = new _model_admin_ChartFelxModel__WEBPACK_IMPORTED_MODULE_3__.default();
    return _this;
  }

  _createClass(ChartConfig, [{
    key: "onClickHandle",
    value: function onClickHandle() {
      if (this.props.onApply) {
        this.props.onApply({
          title: this.state.title,
          symbol: this.state.symbol,
          height: this.state.height,
          configs: this.state.configs,
          database: this.state.database
        });
      }
    }
  }, {
    key: "setConfig",
    value: function setConfig(config) {
      var title = get(config['title'], '');
      var symbol = get(config['symbol'], '');
      var configs = get(config['configs'], []);
      var database = get(config['database'], 'backtest_data');
      var srcOption = {
        '': {
          value: '',
          label: '-- Select Source --'
        }
      };
      var fieldOption = {};
      var symbol_options = [{
        value: symbol,
        label: symbol
      }];

      var _iterator = _createForOfIteratorHelper(configs),
          _step;

      try {
        for (_iterator.s(); !(_step = _iterator.n()).done;) {
          var cfg = _step.value;
          srcOption[cfg['source_data']] = {
            value: cfg['source_data'],
            label: cfg['source_data'].toUpperCase()
          };
          if (!fieldOption[cfg['source_data']]) fieldOption[cfg['source_data']] = {};
          fieldOption[cfg['source_data']][cfg['source_field']] = {
            value: cfg['source_field'],
            label: cfg['source_field'].toUpperCase()
          };
        }
      } catch (err) {
        _iterator.e(err);
      } finally {
        _iterator.f();
      }

      for (var src in fieldOption) {
        fieldOption[src] = Object.values(fieldOption[src]);
      }

      this.setState({
        configs: configs,
        title: title,
        symbol: symbol,
        database: database,
        height: get(config['height'], 250),
        source_data_options: Object.values(srcOption),
        source_field_options: fieldOption,
        symbol_options: symbol_options
      });
    }
  }, {
    key: "modal",
    value: function modal() {
      var _this2 = this;

      var cmd = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : 'show';

      if (cmd == 'hide') {
        $("#edit_row_modal" + this.id).modal('hide');
      } else {
        $("#edit_row_modal" + this.id).modal();
        this.model.getDatabase().then(function (res) {
          if (res) {
            _this2.setState({
              database_options: res
            });
          }
        });
      }
    }
  }, {
    key: "changeOrder",
    value: function changeOrder(src_id, des_id) {
      src_id = Number(src_id);
      des_id = Number(des_id);
      var variables = this.state.configs;

      if (src_id > des_id) {
        variables.splice(des_id, 0, variables[src_id]);
        variables.splice(src_id + 1, 1);
      }

      if (des_id > src_id) {
        variables.splice(des_id + 1, 0, variables[src_id]);
        variables.splice(src_id, 1);
      }

      this.setState({
        variables: variables
      });
    }
  }, {
    key: "render",
    value: function render() {
      var _this3 = this;

      var configs = this.state.configs;
      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
        className: "modal fade",
        id: "edit_row_modal" + this.id,
        onClick: function onClick() {
          addClass($('body')[0], 'modal-open');
        },
        children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
          className: "modal-dialog modal-lg modal-dialog-centered",
          style: {
            maxWidth: '90%'
          },
          children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
            className: "modal-content",
            children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
              className: "modal-header",
              children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("h4", {
                className: "modal-title",
                children: this.state.title
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("button", {
                type: "button",
                className: "close",
                "data-dismiss": "modal",
                children: "\xD7"
              })]
            }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
              className: "modal-body",
              style: {
                textAlign: 'initial'
              },
              children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                className: "box_flex",
                style: {
                  padding: 2
                },
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 5
                  },
                  children: "Title:"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 5
                  },
                  children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                    className: "input",
                    type: "text",
                    Direct: true,
                    Options: this.state.symbol_options,
                    value: this.state.title,
                    OnChange: function OnChange(value, obj) {
                      var update = {
                        title: value
                      };

                      _this3.setState(update);
                    }
                  })
                })]
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                className: "box_flex",
                style: {
                  padding: 2
                },
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 5
                  },
                  children: "Height:"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 5
                  },
                  children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                    className: "input",
                    type: "number",
                    Direct: true,
                    value: this.state.height,
                    OnChange: function OnChange(value, obj) {
                      var update = {
                        height: value
                      };

                      _this3.setState(update);
                    }
                  })
                })]
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                className: "box_flex",
                style: {
                  padding: 2
                },
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 5
                  },
                  children: "Symbol:"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 5
                  },
                  children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                    className: "input",
                    type: "select",
                    Direct: true,
                    Options: this.state.symbol_options,
                    value: this.state.symbol,
                    OnChange: function OnChange(value, obj) {
                      var update = {
                        symbol: value
                      };
                      if (_this3.state.title == '') update['title'] = value;else update['title'] = _this3.state.title.replace(_this3.state.symbol, value);

                      _this3.setState(update);
                    },
                    onClick: function onClick() {
                      _this3.model.getWatchlist().then(function (res) {
                        res ? _this3.setState({
                          symbol_options: res
                        }) : _this3.setState({
                          symbol_options: []
                        });
                      });
                    }
                  })
                })]
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                className: "box_flex",
                style: {
                  padding: 2
                },
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 5
                  },
                  children: "Database:"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 5
                  },
                  children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                    className: "input",
                    type: "select",
                    Direct: true,
                    Options: this.state.database_options,
                    value: this.state.database,
                    OnChange: function OnChange(value, obj) {
                      var update = {
                        database: value
                      };

                      _this3.setState(update);
                    }
                  })
                })]
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("hr", {}), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                className: "box_flex",
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 5,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Source"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 5,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Field"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 5,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Name"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 2,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Frame(m)"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 2,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Agg"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 2,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Type"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 2,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Dash"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 1,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Color 1"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 1,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Color 2"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 1,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Color 3"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 1,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Color 4"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 3,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Magic"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    flex: 1,
                    padding: 2,
                    textAlign: 'center',
                    fontWeight: 'bold'
                  },
                  children: "Delete"
                })]
              }), configs.map(function (item, key) {
                return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_common_DragSort__WEBPACK_IMPORTED_MODULE_4__.default, {
                  style: {
                    textAlign: 'center'
                  },
                  changeOrder: function changeOrder(src_id, des_id) {
                    _this3.changeOrder(src_id, des_id);
                  },
                  src_weight: key,
                  src_id: key,
                  icon: false,
                  children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                    className: "box_flex",
                    children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 5,
                        padding: 2
                      },
                      children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                        className: "input",
                        type: "select",
                        Direct: true,
                        Options: _this3.state.source_data_options,
                        value: item['source_data'],
                        OnChange: function OnChange(value, obj) {
                          item['source_data'] = value;
                          var matched = /candle_(\d*\w*)/gm.exec(value);

                          if (matched) {
                            item['timeframe'] = Math.floor(interval2second(matched[1]) / 60);
                          }

                          _this3.setState({
                            configs: configs
                          });
                        },
                        onClick: function onClick() {
                          _this3.model.getSourceOptions(_this3.state.database).then(function (res) {
                            res ? _this3.setState({
                              source_data_options: res
                            }) : _this3.setState({
                              source_data_options: []
                            });
                          });
                        }
                      })
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 5,
                        padding: 2
                      },
                      children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                        className: "input",
                        type: "select",
                        Direct: true,
                        Options: _this3.state.source_field_options[item['source_data']],
                        value: item['source_field'],
                        OnChange: function OnChange(value, obj) {
                          item['source_field'] = value;
                          item['name'] = value.toUpperCase();
                          var matched = /^([a-zA-Z]*)_([a-zA-Z\d]+)_(\d+)_(\d+)/gm.exec(value);

                          if (matched) {
                            item['timeframe'] = Math.floor(matched[4]);
                          }

                          _this3.setState({
                            configs: configs
                          });
                        },
                        onClick: function onClick() {
                          _this3.model.getChartField(_this3.state.database, item['source_data']).then(function (res) {
                            if (res) {
                              _this3.state.source_field_options[item['source_data']] = res;
                            } else {
                              _this3.state.source_field_options[item['source_data']] = [];
                            }

                            _this3.setState({
                              source_field_options: _this3.state.source_field_options
                            });
                          });
                        }
                      })
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 5,
                        padding: 2
                      },
                      children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                        className: "input",
                        type: "text",
                        Direct: true,
                        value: item['name'],
                        OnChange: function OnChange(value, obj) {
                          item['name'] = value;

                          _this3.setState({
                            configs: configs
                          });
                        }
                      })
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 2,
                        padding: 2
                      },
                      children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                        className: "input",
                        type: "number",
                        Direct: true,
                        Options: _this3.state.type_options,
                        value: item['timeframe'],
                        OnChange: function OnChange(value, obj) {
                          item['timeframe'] = value;

                          _this3.setState({
                            configs: configs
                          });
                        }
                      })
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 2,
                        padding: 2
                      },
                      children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                        className: "input",
                        type: "select",
                        Direct: true,
                        Options: _this3.state.agg_optipons,
                        value: item['agg'],
                        OnChange: function OnChange(value, obj) {
                          item['agg'] = value;

                          _this3.setState({
                            configs: configs
                          });
                        }
                      })
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 2,
                        padding: 2
                      },
                      children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                        className: "input",
                        type: "select",
                        Direct: true,
                        Options: _this3.state.type_options,
                        value: item['type'],
                        OnChange: function OnChange(value, obj) {
                          item['type'] = value;

                          if (value == 'bar_histogram' || value == 'candlestick') {
                            item['color_1'] = '#ff004c';
                            item['color_2'] = '#ffc6d1';
                            item['color_3'] = '#00af9b';
                            item['color_4'] = '#9fe4dc';
                          } else {
                            item['color_1'] = '#' + Math.random().toString(16).slice(-6);
                          }

                          if (value == 'candlestick') {
                            item['source_field'] = 'close';
                          }

                          _this3.setState({
                            configs: configs
                          });
                        }
                      })
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 2,
                        padding: 2
                      },
                      children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                        disabled: item['type'] != 'line',
                        className: "input",
                        type: "select",
                        Direct: true,
                        Options: _this3.state.dash_options,
                        value: item['dash'],
                        OnChange: function OnChange(value, obj) {
                          item['dash'] = value;

                          _this3.setState({
                            configs: configs
                          });
                        }
                      })
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 1,
                        fontSize: 8,
                        padding: 2
                      },
                      children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                        className: "input",
                        type: "color",
                        Direct: true,
                        value: item['color_1'],
                        OnChange: function OnChange(value, obj) {
                          console.log(value);
                          item['color_1'] = value;

                          _this3.setState({
                            configs: configs
                          });
                        }
                      })
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 1,
                        fontSize: 8,
                        padding: 2
                      },
                      children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                        className: "input",
                        type: "color",
                        Direct: true,
                        value: item['color_2'],
                        OnChange: function OnChange(value, obj) {
                          item['color_2'] = value;

                          _this3.setState({
                            configs: configs
                          });
                        }
                      })
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 1,
                        fontSize: 8,
                        padding: 2
                      },
                      children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                        className: "input",
                        type: "color",
                        Direct: true,
                        value: item['color_3'],
                        OnChange: function OnChange(value, obj) {
                          item['color_3'] = value;

                          _this3.setState({
                            configs: configs
                          });
                        }
                      })
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 1,
                        fontSize: 8,
                        padding: 2
                      },
                      children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                        className: "input",
                        type: "color",
                        Direct: true,
                        value: item['color_4'],
                        OnChange: function OnChange(value, obj) {
                          item['color_4'] = value;

                          _this3.setState({
                            configs: configs
                          });
                        }
                      })
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 3,
                        padding: 2
                      },
                      children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_2__.default, {
                        className: "input",
                        type: "text",
                        Direct: true,
                        value: item['magic'],
                        OnChange: function OnChange(value, obj) {
                          item['magic'] = value;

                          _this3.setState({
                            configs: configs
                          });
                        }
                      })
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                      style: {
                        width: 0,
                        flex: 1,
                        padding: 2,
                        fontWeight: 'bold',
                        fontSize: 24,
                        textAlign: 'center'
                      },
                      className: "button",
                      onClick: function onClick() {
                        configs.splice(key, 1);

                        _this3.setState({
                          configs: configs
                        });
                      },
                      children: "\xD7"
                    })]
                  })
                }, key);
              })]
            }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
              className: "modal-footer",
              children: [isset(this.props.extraFunction) ? this.props.extraFunction : '', /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("button", {
                type: "button",
                className: "btn btn-primary",
                onClick: function onClick() {
                  configs.push({
                    'source_data': '',
                    'source_field': '',
                    'name': '',
                    'type': '',
                    'dash': '',
                    'agg': 'last',
                    'timeframe': '',
                    'color_1': '',
                    'color_2': '',
                    'color_3': '',
                    'color_4': '',
                    'magic': ''
                  });

                  _this3.setState({
                    configs: configs
                  });
                },
                children: lang('Add')
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("button", {
                type: "button",
                className: "btn btn-warning",
                onClick: function onClick() {
                  _this3.onClickHandle(1);
                },
                children: lang('Apply')
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("button", {
                type: "button",
                className: "btn btn-danger",
                "data-dismiss": "modal",
                children: lang('Close')
              })]
            })]
          })
        })
      });
    }
  }]);

  return ChartConfig;
}(react__WEBPACK_IMPORTED_MODULE_1__.Component);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (ChartConfig);

/***/ }),

/***/ "./resources/simulation/components/admin/ChartFlex/ChartFlexItem.js":
/*!**************************************************************************!*\
  !*** ./resources/simulation/components/admin/ChartFlex/ChartFlexItem.js ***!
  \**************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-runtime */ "./node_modules/react/jsx-runtime.js");
/* harmony import */ var _babel_runtime_regenerator__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @babel/runtime/regenerator */ "./node_modules/@babel/runtime/regenerator/index.js");
/* harmony import */ var _babel_runtime_regenerator__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_babel_runtime_regenerator__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! react */ "./node_modules/react/index.js");
/* harmony import */ var _model_admin_ChartFelxModel__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ../../../model/admin/ChartFelxModel */ "./resources/simulation/model/admin/ChartFelxModel.js");
/* harmony import */ var _ChartConfig__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./ChartConfig */ "./resources/simulation/components/admin/ChartFlex/ChartConfig.js");
/* harmony import */ var _common_Loading__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ../../common/Loading */ "./resources/simulation/components/common/Loading.js");
/* harmony import */ var _ChartClone__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./ChartClone */ "./resources/simulation/components/admin/ChartFlex/ChartClone.js");
/* harmony import */ var _model_control_Ctrl__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! ../../../model/control/Ctrl */ "./resources/simulation/model/control/Ctrl.js");
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }




function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }



function asyncGeneratorStep(gen, resolve, reject, _next, _throw, key, arg) { try { var info = gen[key](arg); var value = info.value; } catch (error) { reject(error); return; } if (info.done) { resolve(value); } else { Promise.resolve(value).then(_next, _throw); } }

function _asyncToGenerator(fn) { return function () { var self = this, args = arguments; return new Promise(function (resolve, reject) { var gen = fn.apply(self, args); function _next(value) { asyncGeneratorStep(gen, resolve, reject, _next, _throw, "next", value); } function _throw(err) { asyncGeneratorStep(gen, resolve, reject, _next, _throw, "throw", err); } _next(undefined); }); }; }

function _createForOfIteratorHelper(o, allowArrayLike) { var it = typeof Symbol !== "undefined" && o[Symbol.iterator] || o["@@iterator"]; if (!it) { if (Array.isArray(o) || (it = _unsupportedIterableToArray(o)) || allowArrayLike && o && typeof o.length === "number") { if (it) o = it; var i = 0; var F = function F() {}; return { s: F, n: function n() { if (i >= o.length) return { done: true }; return { done: false, value: o[i++] }; }, e: function e(_e) { throw _e; }, f: F }; } throw new TypeError("Invalid attempt to iterate non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); } var normalCompletion = true, didErr = false, err; return { s: function s() { it = it.call(o); }, n: function n() { var step = it.next(); normalCompletion = step.done; return step; }, e: function e(_e2) { didErr = true; err = _e2; }, f: function f() { try { if (!normalCompletion && it["return"] != null) it["return"](); } finally { if (didErr) throw err; } } }; }

function _unsupportedIterableToArray(o, minLen) { if (!o) return; if (typeof o === "string") return _arrayLikeToArray(o, minLen); var n = Object.prototype.toString.call(o).slice(8, -1); if (n === "Object" && o.constructor) n = o.constructor.name; if (n === "Map" || n === "Set") return Array.from(o); if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen); }

function _arrayLikeToArray(arr, len) { if (len == null || len > arr.length) len = arr.length; for (var i = 0, arr2 = new Array(len); i < len; i++) { arr2[i] = arr[i]; } return arr2; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

function _createSuper(Derived) { var hasNativeReflectConstruct = _isNativeReflectConstruct(); return function _createSuperInternal() { var Super = _getPrototypeOf(Derived), result; if (hasNativeReflectConstruct) { var NewTarget = _getPrototypeOf(this).constructor; result = Reflect.construct(Super, arguments, NewTarget); } else { result = Super.apply(this, arguments); } return _possibleConstructorReturn(this, result); }; }

function _possibleConstructorReturn(self, call) { if (call && (_typeof(call) === "object" || typeof call === "function")) { return call; } else if (call !== void 0) { throw new TypeError("Derived constructors may only return object or undefined"); } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _isNativeReflectConstruct() { if (typeof Reflect === "undefined" || !Reflect.construct) return false; if (Reflect.construct.sham) return false; if (typeof Proxy === "function") return true; try { Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function () {})); return true; } catch (e) { return false; } }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }








var ChartFlexItem = /*#__PURE__*/function (_Component) {
  _inherits(ChartFlexItem, _Component);

  var _super = _createSuper(ChartFlexItem);

  function ChartFlexItem(props) {
    var _this;

    _classCallCheck(this, ChartFlexItem);

    _this = _super.call(this, props);
    _this.id = 'plot' + makeId();
    _this.ctrl = new _model_control_Ctrl__WEBPACK_IMPORTED_MODULE_7__.default();
    _this.storageId = _this.props.id;
    var chartConfig = localStorage.getItem(_this.storageId);

    if (chartConfig == null) {
      chartConfig = [];
    } else {
      chartConfig = JSON.parse(chartConfig);
    }

    _this.setChartConfig(chartConfig);

    _this.config = {
      data: [],
      layout: {
        height: get(_this.chartConfig['height'], 300),
        title: get(_this.chartConfig['title'], null),
        autosize: true,
        hovermode: "x unified",
        hoverdistance: 10,
        margin: {
          b: 40,
          t: 40,
          l: 40,
          r: 40
        },
        xaxis: {
          autorange: true,
          type: "category",
          categoryorder: 'category ascending',
          rangeslider: {
            'visible': false
          },
          showspikes: true,
          spikemode: 'across',
          spikesnap: 'cursor',
          spikedash: 'dot',
          spikecolor: 'black',
          spikethickness: 1
        },
        yaxis: {
          autorange: true,
          showspikes: true,
          spikemode: 'across',
          spikesnap: 'cursor',
          spikedash: 'dot',
          spikecolor: 'black',
          spikethickness: 1
        },
        barmode: 'group',
        font: {
          size: 10
        },
        shapes: [{
          type: 'line',
          xref: 'x',
          yref: 'paper',
          x0: 0,
          y0: 0,
          x1: 0,
          y1: 0,
          line: {
            color: 'black',
            width: 1,
            dash: 'dot'
          }
        }],
        legend: {
          yanchor: "top",
          y: 1,
          xanchor: "left",
          x: 0.9
        }
      }
    };
    _this.model = new _model_admin_ChartFelxModel__WEBPACK_IMPORTED_MODULE_3__.default();
    return _this;
  }

  _createClass(ChartFlexItem, [{
    key: "setChartConfig",
    value: function setChartConfig(chartConfig) {
      this.chartConfig = chartConfig;
      var configs = get(this.chartConfig['configs'], []);
      var timeframe = null;

      var _iterator = _createForOfIteratorHelper(configs),
          _step;

      try {
        for (_iterator.s(); !(_step = _iterator.n()).done;) {
          var conf = _step.value;
          var temp = get(conf['timeframe'], 1);
          if (temp == '') temp = 1;

          if (timeframe === null) {
            timeframe = temp;
          } else {
            if (timeframe > temp) timeframe = temp;
          }
        }
      } catch (err) {
        _iterator.e(err);
      } finally {
        _iterator.f();
      }

      this.minTimeFrame = timeframe;

      if (this.props.isPosition && App.parsed.symbol) {
        this.chartConfig['symbol'] = App.parsed.symbol;
        this.chartConfig['title'] = App.parsed.symbol;
      }
    }
  }, {
    key: "updateLayout",
    value: function updateLayout() {
      var currentLayout = this.plot.layout;
      currentLayout['title'] = {
        'text': get(this.chartConfig['title'], null)
      };
      currentLayout['height'] = get(this.chartConfig['height'], 300);
      Plotly.relayout(this.plot, currentLayout);
    }
  }, {
    key: "getData",
    value: function getData() {
      var _this2 = this;

      var _this$props$parent$ge = this.props.parent.getTimeRange(),
          startTime = _this$props$parent$ge.startTime,
          stopTime = _this$props$parent$ge.stopTime;

      if (startTime == '' || stopTime == '') return;
      if (this.chartConfig.length == 0) return;
      this.loading.loading(true, 'Get Data...');
      this.model.getData(this.chartConfig, startTime, stopTime).then(function (res) {
        _this2.loading.loading(false);

        if (res) {
          _this2.updateData(res);
        }
      });
    }
  }, {
    key: "updateAllData",
    value: function () {
      var _updateAllData = _asyncToGenerator( /*#__PURE__*/_babel_runtime_regenerator__WEBPACK_IMPORTED_MODULE_1___default().mark(function _callee() {
        return _babel_runtime_regenerator__WEBPACK_IMPORTED_MODULE_1___default().wrap(function _callee$(_context) {
          while (1) {
            switch (_context.prev = _context.next) {
              case 0:
                if (!this.props.isPosition) {
                  _context.next = 3;
                  break;
                }

                _context.next = 3;
                return this.getPosition();

              case 3:
                this.getData();

              case 4:
              case "end":
                return _context.stop();
            }
          }
        }, _callee, this);
      }));

      function updateAllData() {
        return _updateAllData.apply(this, arguments);
      }

      return updateAllData;
    }()
  }, {
    key: "updateData",
    value: function updateData(datas) {
      var _this3 = this;

      var chartData = [];
      var configIndex = {};

      for (var index in this.chartConfig['configs']) {
        var conf = this.chartConfig['configs'][index];
        var type = get(conf['type'], 'line');
        var id = conf['source_data'] + "_" + conf['name'];
        if (!configIndex[id]) configIndex[id] = [];
        configIndex[id].push(index);

        if (type == 'line') {
          chartData[index] = {
            name: conf['name'],
            mode: 'lines',
            x: [],
            y: [],
            line: {
              color: conf['color_1'],
              dash: get(conf['dash'], 'solid')
            }
          };
        } else if (type == 'bar') {
          chartData[index] = {
            name: conf['name'],
            type: 'bar',
            x: [],
            y: [],
            marker: {
              color: conf['color_1']
            }
          };
        } else if (type == 'bar_histogram') {
          chartData[index] = {
            name: conf['name'],
            type: 'bar',
            x: [],
            y: [],
            marker: {
              color: []
            }
          };
        } else if (type == 'candlestick') {
          chartData[index] = {
            name: conf['name'],
            type: 'candlestick',
            x: [],
            close: [],
            high: [],
            low: [],
            open: [],
            increasing: {
              line: {
                color: conf['color_3'],
                width: 1
              },
              fillcolor: conf['color_4']
            },
            decreasing: {
              line: {
                color: conf['color_1'],
                width: 1
              },
              fillcolor: conf['color_2']
            }
          };
        }
      }

      var periodRow = null;

      for (var coll in datas) {
        var rows = datas[coll];

        var _iterator2 = _createForOfIteratorHelper(rows),
            _step2;

        try {
          for (_iterator2.s(); !(_step2 = _iterator2.n()).done;) {
            var row = _step2.value;
            var timestamp = moment(row['timestamp'], 'X').format();

            for (var field in row) {
              var _id = coll + "_" + field;

              if (configIndex[_id]) {
                var _iterator3 = _createForOfIteratorHelper(configIndex[_id]),
                    _step3;

                try {
                  for (_iterator3.s(); !(_step3 = _iterator3.n()).done;) {
                    var _index = _step3.value;

                    chartData[_index]['x'].push(timestamp);

                    var _conf = this.chartConfig['configs'][_index];

                    var _type = get(_conf['type'], 'line');

                    if (_type == 'line') {
                      chartData[_index]['y'].push(row[field]);
                    } else if (_type == 'bar') {
                      chartData[_index]['y'].push(row[field]);
                    } else if (_type == 'bar_histogram') {
                      chartData[_index]['y'].push(row[field]);

                      if (periodRow === null) {
                        if (row[field] >= 0) chartData[_index]['marker']['color'].push(_conf['color_3']);else chartData[_index]['marker']['color'].push(_conf['color_1']);
                      } else {
                        if (row[field] >= 0 && row[field] >= periodRow[field]) chartData[_index]['marker']['color'].push(_conf['color_3']);else if (row[field] >= 0 && row[field] < periodRow[field]) chartData[_index]['marker']['color'].push(_conf['color_4']);else if (row[field] < 0 && row[field] >= periodRow[field]) chartData[_index]['marker']['color'].push(_conf['color_2']);else if (row[field] < 0 && row[field] < periodRow[field]) chartData[_index]['marker']['color'].push(_conf['color_1']);
                      }
                    } else if (_type == 'candlestick') {
                      chartData[_index]['close'].push(row['close']);

                      chartData[_index]['open'].push(row['open']);

                      chartData[_index]['low'].push(row['low']);

                      chartData[_index]['high'].push(row['high']);
                    }
                  }
                } catch (err) {
                  _iterator3.e(err);
                } finally {
                  _iterator3.f();
                }
              }
            }

            periodRow = row;
          }
        } catch (err) {
          _iterator2.e(err);
        } finally {
          _iterator2.f();
        }
      } //update to chart


      if (this.positionOpenData) chartData.push(this.positionOpenData);
      if (this.positionCloseData) chartData.push(this.positionCloseData);
      if (this.orderData) chartData.push(this.orderData);
      Plotly.newPlot(this.plot, chartData, this.config.layout).then(function () {
        _this3.syncChart();
      }); // for(let id in chartData){
      //     let data = chartData[id]
      //     Plotly.restyle(this.plot, data, [id])
      // }
    }
  }, {
    key: "getPosition",
    value: function getPosition() {
      var _this4 = this;

      var _this$props$parent$ge2 = this.props.parent.getTimeRange(),
          startTime = _this$props$parent$ge2.startTime,
          stopTime = _this$props$parent$ge2.stopTime;

      if (startTime == '' || stopTime == '') return Promise.resolve();
      var account = this.props.parent.getAccount();
      if (account == '') return Promise.resolve();
      var symbol = this.chartConfig['symbol'];
      if (!symbol) return Promise.resolve();
      return this.model.getPosition(account, symbol, startTime * 1000, stopTime * 1000).then(function (res) {
        if (res) {
          return _this4.drawPosition(res);
        }
      });
    }
  }, {
    key: "drawPosition",
    value: function drawPosition(data) {
      var _this$props$parent$ge3 = this.props.parent.getTimeRange(),
          startTime = _this$props$parent$ge3.startTime,
          stopTime = _this$props$parent$ge3.stopTime;

      this.positionOpenData = {
        x: [],
        y: [],
        name: "Position Open",
        marker: {
          color: "red",
          size: 8
        },
        mode: "markers+text",
        text: [],
        textposition: "top center",
        textfont: {
          color: "red"
        },
        type: 'scatter'
      };
      this.positionCloseData = {
        x: [],
        y: [],
        name: "Position Close",
        marker: {
          color: "orange",
          size: 8
        },
        mode: "markers+text",
        text: [],
        textposition: "top center",
        textfont: {
          color: "orange"
        },
        type: 'scatter'
      };
      this.orderData = {
        x: [],
        y: [],
        name: "Orders",
        visible: 'legendonly',
        marker: {
          color: [],
          size: 8,
          symbol: 'square'
        },
        mode: "markers+text",
        text: [],
        textposition: "top center",
        textfont: {
          color: "green"
        },
        type: 'scatter'
      };

      var _iterator4 = _createForOfIteratorHelper(data['position']),
          _step4;

      try {
        for (_iterator4.s(); !(_step4 = _iterator4.n()).done;) {
          var position = _step4.value;
          var timestampStart = moment(position[LAB_RESULT_CHART], 'x').format();
          this.positionOpenData.x.push(timestampStart);
          this.positionOpenData.y.push(position[LAB_RESULT_CHART_PRICE]);
          this.positionOpenData.text.push(position[LAB_RESULT_TYPE] == LAB_RESULT_TYPE_LONG ? 'B' : 'S');

          if (position[LAB_RESULT_SELL_TIME] > 0 && position[LAB_RESULT_SELL_TIME] <= stopTime * 1000) {
            var timestampStop = moment(position[LAB_RESULT_SELL_TIME], 'x').format();
            this.positionCloseData.x.push(timestampStop);
            this.positionCloseData.y.push(position[LAB_RESULT_SELL_PRICE]);
            this.positionCloseData.text.push(position[LAB_RESULT_REAL_PNL] > 0 ? 'TP' : 'SL');
          }
        }
      } catch (err) {
        _iterator4.e(err);
      } finally {
        _iterator4.f();
      }

      var _iterator5 = _createForOfIteratorHelper(data['orders']),
          _step5;

      try {
        for (_iterator5.s(); !(_step5 = _iterator5.n()).done;) {
          var order = _step5.value;
          var timestampStart = moment(order[LAB_ORDER_TIME], 'x').format();
          this.orderData.x.push(timestampStart);
          this.orderData.y.push(order[LAB_ORDER_PRICE]);
          this.orderData.text.push("<b>" + (order[LAB_ORDER_TYPE] == LAB_RESULT_TYPE_LONG ? 'B' : 'S') + '' + order[LAB_ORDER_PHASE] + "</b>");
          this.orderData.marker.color.push(order[LAB_ORDER_TYPE] == LAB_RESULT_TYPE_LONG ? 'green' : 'red');
        } // console.log(this.positionOpenData)

      } catch (err) {
        _iterator5.e(err);
      } finally {
        _iterator5.f();
      }
    }
  }, {
    key: "syncChart",
    value: function syncChart() {
      var _this5 = this;

      if (this.props.sync) {
        this.props.sync.register(this.id, this); //sync hover

        this.plot.on('plotly_hover', function (data) {
          // this.props.sync.updateHover(this.id, data.xvals[0])
          _this5.props.sync.updateHover(_this5.id, data.points[0].x);
        });
        this.plot.on('plotly_relayout', function (data) {
          _this5.props.sync.updateScale(_this5.id, data);
        });
      }
    }
  }, {
    key: "render",
    value: function render() {
      var _this6 = this;

      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
        className: "box_padding box_shadow",
        ref: function ref(c) {
          return _this6.chartContainer = c;
        },
        style: {
          position: 'relative',
          margin: 2,
          minHeight: 50
        },
        children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
          className: "box_flex",
          style: {
            position: 'absolute',
            zIndex: 1
          },
          children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            className: "button",
            onClick: function onClick() {
              _this6.chartConfigCom.modal();

              _this6.chartConfigCom.setConfig(_this6.chartConfig);
            },
            children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("i", {
              className: "fa fa-cog"
            })
          }), "\xA0", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            className: "button",
            onClick: function onClick() {
              _this6.updateAllData();
            },
            children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("i", {
              className: "fa fa-refresh"
            })
          }), "\xA0", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            className: "button",
            onClick: function onClick() {
              _this6.chartCloneCom.modal();

              _this6.chartCloneCom.setConfig(_this6.chartConfig);
            },
            children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("i", {
              className: "fa fa-clone"
            })
          }), "\xA0", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            className: "button",
            onClick: function onClick() {
              _this6.chartConfig.hidden = !_this6.chartConfig.hidden;

              _this6.forceUpdate();
            },
            children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("i", {
              className: "fa fa-window-restore"
            })
          })]
        }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
          style: {
            display: this.chartConfig.hidden ? 'none' : 'block'
          },
          ref: function ref(c) {
            return _this6.plot = c;
          },
          id: this.id
        }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_ChartConfig__WEBPACK_IMPORTED_MODULE_4__.default, {
          ref: function ref(c) {
            return _this6.chartConfigCom = c;
          },
          onApply: function onApply(config) {
            _this6.setChartConfig(config);

            _this6.updateLayout();

            _this6.updateAllData();

            localStorage.setItem(_this6.storageId, JSON.stringify(config));

            _this6.chartConfigCom.modal('hide');
          }
        }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_ChartClone__WEBPACK_IMPORTED_MODULE_6__.default, {
          ref: function ref(c) {
            return _this6.chartCloneCom = c;
          },
          onApply: function onApply(config) {
            _this6.setChartConfig(config);

            _this6.updateLayout();

            _this6.updateAllData();

            localStorage.setItem(_this6.storageId, JSON.stringify(config));

            _this6.chartCloneCom.modal('hide');
          },
          onSetDefault: function onSetDefault(config) {
            _this6.ctrl.set(_defineProperty({}, _this6.storageId, JSON.stringify(config))).then(function (res) {
              if (res) {
                showLog('Configuration is set as Default', 'success');
              }
            });
          }
        }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_common_Loading__WEBPACK_IMPORTED_MODULE_5__.default, {
          style: {
            position: 'absolute'
          },
          ref: function ref(c) {
            return _this6.loading = c;
          }
        })]
      });
    }
  }, {
    key: "componentDidMount",
    value: function () {
      var _componentDidMount = _asyncToGenerator( /*#__PURE__*/_babel_runtime_regenerator__WEBPACK_IMPORTED_MODULE_1___default().mark(function _callee2() {
        var _this7 = this;

        return _babel_runtime_regenerator__WEBPACK_IMPORTED_MODULE_1___default().wrap(function _callee2$(_context2) {
          while (1) {
            switch (_context2.prev = _context2.next) {
              case 0:
                Plotly.newPlot(this.plot, this.config.data, this.config.layout);
                this.resize_ob = new ResizeObserver(function (entries) {
                  if (_this7.resizeTimeOut) clearTimeout(_this7.resizeTimeOut);
                  _this7.resizeTimeOut = setTimeout(function () {
                    console.log('Resize');
                    if (!_this7.chartConfig.hidden) Plotly.Plots.resize(_this7.plot);
                  });
                });
                this.resize_ob.observe(this.chartContainer);

                if (get(this.chartConfig['configs'], []).length == 0) {
                  this.ctrl.get(this.storageId).then(function (res) {
                    if (res) {
                      res = JSON.parse(res);

                      if (res) {
                        _this7.setChartConfig(res);

                        _this7.updateAllData();
                      }
                    }
                  });
                }

                _context2.next = 6;
                return this.updateAllData();

              case 6:
              case "end":
                return _context2.stop();
            }
          }
        }, _callee2, this);
      }));

      function componentDidMount() {
        return _componentDidMount.apply(this, arguments);
      }

      return componentDidMount;
    }()
  }, {
    key: "componentWillUnmount",
    value: function componentWillUnmount() {
      if (this.props.sync) {
        this.props.sync.unregister(this.id);
      }
    }
  }, {
    key: "hover",
    value: function hover(xval) {
      if (xval === null) {
        Plotly.relayout(this.plot, {
          shapes: [{
            visible: false
          }]
        });
      } else {
        if (this.plot.data.length == 0) return;
        var poins = [];
        var x = Math.floor(moment(xval).valueOf() / (this.minTimeFrame * 60000)) * (this.minTimeFrame * 60000);
        x = moment(x).format();
        var index = this.plot.data[0]['x'].indexOf(x);

        if (index != -1) {
          // if(this.orderData) index = index * this.minTimeFrame
          for (var curve in this.plot.data) {
            poins.push({
              curveNumber: curve,
              xval: index
            });
          }

          Plotly.Fx.hover(this.id, poins);
          Plotly.relayout(this.plot, {
            shapes: [{
              type: 'line',
              xref: 'x',
              yref: 'paper',
              x0: index,
              y0: 0,
              x1: index,
              y1: 1,
              line: {
                color: 'black',
                width: 1,
                dash: 'dot'
              }
            }]
          });
        }
      }
    }
  }]);

  return ChartFlexItem;
}(react__WEBPACK_IMPORTED_MODULE_2__.Component);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (ChartFlexItem);

/***/ }),

/***/ "./resources/simulation/components/admin/ChartFlex/ChartSync.js":
/*!**********************************************************************!*\
  !*** ./resources/simulation/components/admin/ChartFlex/ChartSync.js ***!
  \**********************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (/* binding */ ChartSync)
/* harmony export */ });
function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

var ChartSync = /*#__PURE__*/function () {
  function ChartSync() {
    _classCallCheck(this, ChartSync);

    this.charts = {};
  }

  _createClass(ChartSync, [{
    key: "register",
    value: function register(id, obj) {
      this.charts[id] = obj;
    }
  }, {
    key: "unregister",
    value: function unregister(id) {
      delete this.charts[id];
    }
  }, {
    key: "updateXaxis",
    value: function updateXaxis() {}
  }, {
    key: "updateHover",
    value: function updateHover(oid, xval) {
      for (var id in this.charts) {
        var obj = this.charts[id];

        if (id == oid) {
          obj.hover(null);
        } else {
          obj.hover(xval);
        }
      }
    }
  }, {
    key: "updateScale",
    value: function updateScale(oid, data) {
      if (data['xaxis.autorange'] == undefined && data['xaxis.range[0]'] !== undefined) {
        var obj = this.charts[oid];
        var startIndex = Math.floor(data['xaxis.range[0]']);
        var stopIndex = Math.ceil(data['xaxis.range[1]']);
        var xData = obj.plot.data[0]['x'];
        var startValue = xData[startIndex];
        var stopValue = xData[stopIndex];
      }

      for (var id in this.charts) {
        if (id == oid) continue;
        var _obj = this.charts[id];
        var layout = JSON.parse(JSON.stringify(_obj.config.layout));

        if (data === null) {
          layout.xaxis.autorange = true;
          Plotly.relayout(_obj.plot, {
            xaxis: layout.xaxis
          });
          return;
        }

        if (data['xaxis.autorange'] !== undefined) {
          layout.xaxis.autorange = true;
          Plotly.relayout(_obj.plot, {
            xaxis: layout.xaxis
          });
        }

        if (data['xaxis.range[0]'] !== undefined) {
          var _xData = _obj.plot.data[0]['x'];
          var startRange = 0;
          var stopRange = _xData.length;

          for (var i in _xData) {
            if (startRange == 0 && _xData[i] > startValue) {
              startRange = i == 0 ? 0 : i - 1;
            }

            if (stopRange == _xData.length && _xData[i] > stopValue) {
              stopRange = i;
              break;
            }
          }

          var xRange = [startRange, stopRange];
          layout.xaxis.autorange = false;
          layout.xaxis.range = xRange;
          Plotly.relayout(_obj.plot, {
            xaxis: layout.xaxis
          });
        }
      }
    }
  }]);

  return ChartSync;
}();



/***/ }),

/***/ "./resources/simulation/components/common/DragSort.js":
/*!************************************************************!*\
  !*** ./resources/simulation/components/common/DragSort.js ***!
  \************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-runtime */ "./node_modules/react/jsx-runtime.js");
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! react */ "./node_modules/react/index.js");
/* harmony import */ var _Style__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./Style */ "./resources/simulation/components/common/Style.js");
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }




var _excluded = ["className", "changeOrder", "src_id", "src_weight", "icon", "children"];

function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); if (enumerableOnly) { symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; }); } keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i] != null ? arguments[i] : {}; if (i % 2) { ownKeys(Object(source), true).forEach(function (key) { _defineProperty(target, key, source[key]); }); } else if (Object.getOwnPropertyDescriptors) { Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)); } else { ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _objectWithoutProperties(source, excluded) { if (source == null) return {}; var target = _objectWithoutPropertiesLoose(source, excluded); var key, i; if (Object.getOwnPropertySymbols) { var sourceSymbolKeys = Object.getOwnPropertySymbols(source); for (i = 0; i < sourceSymbolKeys.length; i++) { key = sourceSymbolKeys[i]; if (excluded.indexOf(key) >= 0) continue; if (!Object.prototype.propertyIsEnumerable.call(source, key)) continue; target[key] = source[key]; } } return target; }

function _objectWithoutPropertiesLoose(source, excluded) { if (source == null) return {}; var target = {}; var sourceKeys = Object.keys(source); var key, i; for (i = 0; i < sourceKeys.length; i++) { key = sourceKeys[i]; if (excluded.indexOf(key) >= 0) continue; target[key] = source[key]; } return target; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

function _createSuper(Derived) { var hasNativeReflectConstruct = _isNativeReflectConstruct(); return function _createSuperInternal() { var Super = _getPrototypeOf(Derived), result; if (hasNativeReflectConstruct) { var NewTarget = _getPrototypeOf(this).constructor; result = Reflect.construct(Super, arguments, NewTarget); } else { result = Super.apply(this, arguments); } return _possibleConstructorReturn(this, result); }; }

function _possibleConstructorReturn(self, call) { if (call && (_typeof(call) === "object" || typeof call === "function")) { return call; } else if (call !== void 0) { throw new TypeError("Derived constructors may only return object or undefined"); } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _isNativeReflectConstruct() { if (typeof Reflect === "undefined" || !Reflect.construct) return false; if (Reflect.construct.sham) return false; if (typeof Proxy === "function") return true; try { Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function () {})); return true; } catch (e) { return false; } }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }




var DragSort = /*#__PURE__*/function (_Component) {
  _inherits(DragSort, _Component);

  var _super = _createSuper(DragSort);

  function DragSort(props, context) {
    var _this;

    _classCallCheck(this, DragSort);

    _this = _super.call(this, props);
    _this.state = {
      dragover: '',
      dragging: ''
    };
    _this.id = makeId();
    return _this;
  }

  _createClass(DragSort, [{
    key: "onDragStart",
    value: function onDragStart(event) {
      this.setState({
        dragging: 'dragging'
      });
      event.dataTransfer.setData('src_id', this.props.src_id);
      __webpack_require__.g.src_weight = this.props.src_weight;
    }
  }, {
    key: "onDragEnd",
    value: function onDragEnd(event) {
      this.setState({
        dragging: ''
      });
    }
  }, {
    key: "onDrop",
    value: function onDrop(event) {
      event.preventDefault();
      var src_id = event.dataTransfer.getData("src_id");

      if (this.props.changeOrder && src_id != this.props.src_id) {
        this.props.changeOrder(src_id, this.props.src_id);
      }

      this.setState({
        dragover: ''
      });
      delete __webpack_require__.g.src_weight;
    }
  }, {
    key: "onDragEnter",
    value: function onDragEnter(event) {
      event.preventDefault();
      var src_weight = __webpack_require__.g.src_weight;

      if (Number(src_weight) > Number(this.props.src_weight)) {
        this.setState({
          dragover: 'dragover down'
        });
      } else if (Number(src_weight) < Number(this.props.src_weight)) {
        this.setState({
          dragover: 'dragover up'
        });
      }
    }
  }, {
    key: "onDragLeave",
    value: function onDragLeave(event) {
      event.preventDefault();
      this.setState({
        dragover: ''
      });
    }
  }, {
    key: "render",
    value: function render() {
      var _this2 = this;

      var _this$props = this.props,
          className = _this$props.className,
          changeOrder = _this$props.changeOrder,
          src_id = _this$props.src_id,
          src_weight = _this$props.src_weight,
          icon = _this$props.icon,
          children = _this$props.children,
          rent = _objectWithoutProperties(_this$props, _excluded);

      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)(react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.Fragment, {
        children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_Style__WEBPACK_IMPORTED_MODULE_2__.default, {
          id: "drag_sort_css",
          children: "\n\t\t\t\t\t  .dragsort_item.dragover.up::after{\n\t\t\t\t\t\t\tcontent:'';\n\t\t\t\t\t\t\twidth: 100%;\n\t\t\t\t\t\t\theight: 0px;\n\t\t\t\t\t\t\tborder-radius: 5px;\n\t\t\t\t\t\t\tborder: dashed thin orange;\n\t\t\t\t\t\t\tdisplay: block;\n\t\t\t\t  \t  }\n\t\t\t\t\t  .dragsort_item.dragover.down::before{\n\t\t\t\t\t\t\tcontent:'';\n\t\t\t\t\t\t\twidth: 100%;\n\t\t\t\t\t\t\theight: 0px;\n\t\t\t\t\t\t\tborder-radius: 5px;\n\t\t\t\t\t\t\tborder: dashed thin orange;\n\t\t\t\t\t\t\tdisplay: block;\n\t\t\t\t\t\t\t\n\t\t\t\t  \t  }\n\t\t\t\t\t  .dragsort_item {\n\t\t\t\t\t\t  padding: 5px 0px;\n\t\t\t\t\t\t  position: relative;\n\t\t\t\t\t\t  cursor: move;\n\t\t\t\t\t  }\n\t\t\t\t\t  .dragsort_item.dragging{\n\t\t\t\t\t\t  border:solid thin orange;\n\t\t\t\t\t  }\n\t\t\t\t\t  .dragsort_item.dragging * {\n\t\t\t\t\t      pointer-events: none;\n\t\t\t\t\t  }\n\t\t\t\t\t  .dragsort_item.dragover *{\n\t\t\t\t\t\tpointer-events: none;\n\t\t\t\t\t  }\n\t\t\t\t\t  \n\t\t\t\t  "
        }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", _objectSpread(_objectSpread({
          draggable: true,
          className: "dragsort_item ".concat(get(this.props.className, ''), " ").concat(this.state.dragover, " ").concat(this.state.dragging),
          onDragStart: function onDragStart(event) {
            _this2.onDragStart(event);
          },
          onDragEnd: function onDragEnd(event) {
            _this2.onDragEnd(event);
          },
          onDrop: function onDrop(event) {
            _this2.onDrop(event);
          },
          onDragOver: function onDragOver(event) {
            event.preventDefault();
          },
          onDragEnter: function onDragEnter(event) {
            console.log('enter');

            _this2.onDragEnter(event);
          },
          onDragLeave: function onDragLeave(event) {
            console.log('leave');

            _this2.onDragLeave(event);
          }
        }, rent), {}, {
          children: [this.props.icon ? /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("i", {
            className: "fa fa-arrows",
            style: {
              pointerEvents: 'none'
            }
          }) : "", this.props.children]
        }))]
      });
    }
  }]);

  return DragSort;
}(react__WEBPACK_IMPORTED_MODULE_1__.Component);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (DragSort);

/***/ }),

/***/ "./resources/simulation/model/admin/ChartFelxModel.js":
/*!************************************************************!*\
  !*** ./resources/simulation/model/admin/ChartFelxModel.js ***!
  \************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var _Lab_account__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./Lab_account */ "./resources/simulation/model/admin/Lab_account.js");
/* harmony import */ var _Lab_watchlist__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./Lab_watchlist */ "./resources/simulation/model/admin/Lab_watchlist.js");
function _createForOfIteratorHelper(o, allowArrayLike) { var it = typeof Symbol !== "undefined" && o[Symbol.iterator] || o["@@iterator"]; if (!it) { if (Array.isArray(o) || (it = _unsupportedIterableToArray(o)) || allowArrayLike && o && typeof o.length === "number") { if (it) o = it; var i = 0; var F = function F() {}; return { s: F, n: function n() { if (i >= o.length) return { done: true }; return { done: false, value: o[i++] }; }, e: function e(_e) { throw _e; }, f: F }; } throw new TypeError("Invalid attempt to iterate non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); } var normalCompletion = true, didErr = false, err; return { s: function s() { it = it.call(o); }, n: function n() { var step = it.next(); normalCompletion = step.done; return step; }, e: function e(_e2) { didErr = true; err = _e2; }, f: function f() { try { if (!normalCompletion && it["return"] != null) it["return"](); } finally { if (didErr) throw err; } } }; }

function _unsupportedIterableToArray(o, minLen) { if (!o) return; if (typeof o === "string") return _arrayLikeToArray(o, minLen); var n = Object.prototype.toString.call(o).slice(8, -1); if (n === "Object" && o.constructor) n = o.constructor.name; if (n === "Map" || n === "Set") return Array.from(o); if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen); }

function _arrayLikeToArray(arr, len) { if (len == null || len > arr.length) len = arr.length; for (var i = 0, arr2 = new Array(len); i < len; i++) { arr2[i] = arr[i]; } return arr2; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }




var ChartFelxModel = /*#__PURE__*/function () {
  function ChartFelxModel() {
    _classCallCheck(this, ChartFelxModel);

    this.getChartFieldResult = {};
  }

  _createClass(ChartFelxModel, [{
    key: "getDatabase",
    value: function getDatabase() {
      if (this.getDatabaseResult) return this.getDatabaseResult;
      App.loading(true, 'Loading...');
      this.getDatabaseResult = axios.request({
        url: '/admin/chartflex/getDatabase',
        method: 'POST'
      }).then(function (response) {
        App.loading(false, 'Loading...');
        response = response['data'];

        if (response['result']) {
          response = response['data'];
          var options = [{
            'value': '',
            'label': '-- Select Database --'
          }];

          for (var db in response) {
            options.push({
              'value': db,
              'label': response[db]
            });
          }

          return options;
        } else {
          error_handle(response);
        }
      })["catch"](function (error) {
        console.log(error);
        App.loading(false, 'Loading...');
        error_handle(error);
        return false;
      });
      return this.getDatabaseResult;
    }
  }, {
    key: "getSourceOptions",
    value: function getSourceOptions(database) {
      if (this.getSourceOptionsResult) return this.getSourceOptionsResult;
      App.loading(true, 'Loading...');
      this.getSourceOptionsResult = axios.request({
        url: '/admin/chartflex/getChartSource',
        method: 'POST',
        data: {
          database: database
        }
      }).then(function (response) {
        App.loading(false, 'Loading...');
        response = response['data'];

        if (response['result']) {
          response = response['data'];
          var options = [{
            'value': '',
            'label': '-- Select Source --'
          }];

          var _iterator = _createForOfIteratorHelper(response),
              _step;

          try {
            for (_iterator.s(); !(_step = _iterator.n()).done;) {
              var db = _step.value;
              options.push({
                'value': db,
                'label': db.toUpperCase()
              });
            }
          } catch (err) {
            _iterator.e(err);
          } finally {
            _iterator.f();
          }

          return options;
        } else {
          error_handle(response);
        }
      })["catch"](function (error) {
        console.log(error);
        App.loading(false, 'Loading...');
        error_handle(error);
        return false;
      });
      return this.getSourceOptionsResult;
    }
  }, {
    key: "getChartField",
    value: function getChartField(database, source) {
      if (!source) return Promise.resolve([]);
      if (this.getChartFieldResult[source]) return this.getChartFieldResult[source];
      App.loading(true, 'Loading...');
      this.getChartFieldResult[source] = axios.request({
        url: '/admin/chartflex/getChartField',
        method: 'POST',
        data: {
          database: database,
          source: source
        }
      }).then(function (response) {
        App.loading(false, 'Loading...');
        response = response['data'];

        if (response['result']) {
          response = response['data'];
          var options = [{
            'value': '',
            'label': '-- Select Field --'
          }];

          var _iterator2 = _createForOfIteratorHelper(response),
              _step2;

          try {
            for (_iterator2.s(); !(_step2 = _iterator2.n()).done;) {
              var db = _step2.value;
              options.push({
                'value': db,
                'label': db.toUpperCase()
              });
            }
          } catch (err) {
            _iterator2.e(err);
          } finally {
            _iterator2.f();
          }

          return options;
        } else {
          error_handle(response);
        }
      })["catch"](function (error) {
        console.log(error);
        App.loading(false, 'Loading...');
        error_handle(error);
        return false;
      });
      return this.getChartFieldResult[source];
    }
  }, {
    key: "getWatchlist",
    value: function getWatchlist() {
      if (this.getWatchlistResult) return this.getWatchlistResult;
      App.loading(true);
      this.wlModel = new _Lab_watchlist__WEBPACK_IMPORTED_MODULE_1__.default();
      this.getWatchlistResult = this.wlModel.read().then(function (res) {
        if (res) {
          if (res['result']) {
            var data = res['data'].sort(function (a, b) {
              return a[LAB_WL_SYMBOL] > b[LAB_WL_SYMBOL] ? 1 : -1;
            });
            var options = [{
              'value': '',
              'label': '-- Select Symbol --'
            }];
            data.map(function (item) {
              options.push({
                'value': item[LAB_WL_SYMBOL],
                'label': item[LAB_WL_SYMBOL]
              });
            });
            return options;
          }
        }
      });
      return this.getWatchlistResult;
    }
  }, {
    key: "getLabAccounts",
    value: function getLabAccounts() {
      App.loading(true);
      this.accountModel = new _Lab_account__WEBPACK_IMPORTED_MODULE_0__.default();
      return this.accountModel.read().then(function (res) {
        if (res) {
          if (res['result']) {
            var data = res['data'].sort(function (a, b) {
              return a[LAB_ACCOUNT_NAME] > b[LAB_ACCOUNT_NAME] ? 1 : -1;
            });
            var options = [{
              'value': '',
              'label': '-- Select Account --'
            }];
            data.map(function (item) {
              options.push({
                'value': item[LAB_ACCOUNT_ID],
                'label': item[LAB_ACCOUNT_NAME]
              });
            });
            return options;
          }
        }
      });
    }
  }, {
    key: "getData",
    value: function getData(config, startTime, stopTime) {
      return axios.request({
        url: '/admin/chartflex/getData',
        method: 'POST',
        data: {
          configuration: config,
          start_time: startTime,
          stop_time: stopTime
        }
      }).then(function (response) {
        response = response['data'];

        if (response['result']) {
          response = response['data'];
          return response;
        } else {
          error_handle(response);
        }
      })["catch"](function (error) {
        console.log(error);
        error_handle(error);
        return false;
      });
    }
  }, {
    key: "getPosition",
    value: function getPosition(account, symbol, startTime, stopTime) {
      return axios.request({
        url: '/admin/chartflex/getPosition',
        method: 'POST',
        data: {
          account: account,
          symbol: symbol,
          startTime: startTime,
          stopTime: stopTime
        }
      }).then(function (response) {
        response = response['data'];

        if (response['result']) {
          response = response['data'];
          return response;
        } else {
          error_handle(response);
        }
      })["catch"](function (error) {
        console.log(error);
        error_handle(error);
        return false;
      });
    }
  }]);

  return ChartFelxModel;
}();

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (ChartFelxModel);

/***/ }),

/***/ "./resources/simulation/model/control/Ctrl.js":
/*!****************************************************!*\
  !*** ./resources/simulation/model/control/Ctrl.js ***!
  \****************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var _model__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../model */ "./resources/simulation/model/model.js");
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

function _createSuper(Derived) { var hasNativeReflectConstruct = _isNativeReflectConstruct(); return function _createSuperInternal() { var Super = _getPrototypeOf(Derived), result; if (hasNativeReflectConstruct) { var NewTarget = _getPrototypeOf(this).constructor; result = Reflect.construct(Super, arguments, NewTarget); } else { result = Super.apply(this, arguments); } return _possibleConstructorReturn(this, result); }; }

function _possibleConstructorReturn(self, call) { if (call && (_typeof(call) === "object" || typeof call === "function")) { return call; } else if (call !== void 0) { throw new TypeError("Derived constructors may only return object or undefined"); } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _isNativeReflectConstruct() { if (typeof Reflect === "undefined" || !Reflect.construct) return false; if (Reflect.construct.sham) return false; if (typeof Proxy === "function") return true; try { Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function () {})); return true; } catch (e) { return false; } }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }



var Ctrl = /*#__PURE__*/function (_model) {
  _inherits(Ctrl, _model);

  var _super = _createSuper(Ctrl);

  function Ctrl() {
    _classCallCheck(this, Ctrl);

    return _super.call(this);
  }

  _createClass(Ctrl, [{
    key: "get",
    value: function get(key) {
      var df = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
      App.loading(true);
      return axios.request({
        url: '/control/control/read',
        method: 'POST',
        data: {
          keys: [key]
        }
      }).then(function (response) {
        App.loading(false, 'Loading...');
        response = response['data'];

        if (response['result']) {
          if (response['data'][key] === null) return df;
          return response['data'][key];
        } else {
          error_handle(response);
          return df;
        }
      })["catch"](function (error) {
        console.log(error);
        App.loading(false, 'Loading...');
        error_handle(error);
        return df;
      });
    }
  }, {
    key: "set",
    value: function set(data) {
      App.loading(true);
      return axios.request({
        url: '/control/control/update',
        method: 'POST',
        data: data
      }).then(function (response) {
        App.loading(false, 'Loading...');
        response = response['data'];

        if (response['result']) {
          return response;
        } else {
          error_handle(response);
          return response;
        }
      })["catch"](function (error) {
        console.log(error);
        App.loading(false, 'Loading...');
        error_handle(error);
        return false;
      });
    }
  }]);

  return Ctrl;
}(_model__WEBPACK_IMPORTED_MODULE_0__.default);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (Ctrl);

/***/ }),

/***/ "./resources/simulation/pages/admin/ChartFlex.js":
/*!*******************************************************!*\
  !*** ./resources/simulation/pages/admin/ChartFlex.js ***!
  \*******************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-runtime */ "./node_modules/react/jsx-runtime.js");
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! react */ "./node_modules/react/index.js");
/* harmony import */ var _components_admin_ChartFlex_ChartFlexItem__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ../../components/admin/ChartFlex/ChartFlexItem */ "./resources/simulation/components/admin/ChartFlex/ChartFlexItem.js");
/* harmony import */ var _components_admin_ChartFlex_ChartSync__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ../../components/admin/ChartFlex/ChartSync */ "./resources/simulation/components/admin/ChartFlex/ChartSync.js");
/* harmony import */ var _components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ../../components/Input_v2/Input */ "./resources/simulation/components/Input_v2/Input.js");
/* harmony import */ var _model_admin_ChartFelxModel__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ../../model/admin/ChartFelxModel */ "./resources/simulation/model/admin/ChartFelxModel.js");
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }




function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

function _createSuper(Derived) { var hasNativeReflectConstruct = _isNativeReflectConstruct(); return function _createSuperInternal() { var Super = _getPrototypeOf(Derived), result; if (hasNativeReflectConstruct) { var NewTarget = _getPrototypeOf(this).constructor; result = Reflect.construct(Super, arguments, NewTarget); } else { result = Super.apply(this, arguments); } return _possibleConstructorReturn(this, result); }; }

function _possibleConstructorReturn(self, call) { if (call && (_typeof(call) === "object" || typeof call === "function")) { return call; } else if (call !== void 0) { throw new TypeError("Derived constructors may only return object or undefined"); } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _isNativeReflectConstruct() { if (typeof Reflect === "undefined" || !Reflect.construct) return false; if (Reflect.construct.sham) return false; if (typeof Proxy === "function") return true; try { Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function () {})); return true; } catch (e) { return false; } }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }







var ChartFlex = /*#__PURE__*/function (_Component) {
  _inherits(ChartFlex, _Component);

  var _super = _createSuper(ChartFlex);

  function ChartFlex(props) {
    var _this;

    _classCallCheck(this, ChartFlex);

    _this = _super.call(this, props);
    _this.id = 'ChartFlex';
    _this.storageAccountKey = "".concat(_this.id, "_account");
    _this.storageStartTime = "".concat(_this.id, "_startTime");
    _this.storageTimeLength = "".concat(_this.id, "_timeLength");
    _this.chartSycn = new _components_admin_ChartFlex_ChartSync__WEBPACK_IMPORTED_MODULE_3__.default();
    _this.state = {
      account: App.parsed.account ? Number(App.parsed.account) : localStorage.getItem(_this.storageAccountKey) ? localStorage.getItem(_this.storageAccountKey) : '',
      timeLeng: localStorage.getItem(_this.storageTimeLength) ? localStorage.getItem(_this.storageTimeLength) : 2,
      startTime: App.parsed.time ? Number(App.parsed.time) : localStorage.getItem(_this.storageStartTime) ? localStorage.getItem(_this.storageStartTime) : Number(moment().startOf('day').subtract(1, 'day').format('X')),
      account_options: []
    };
    return _this;
  }

  _createClass(ChartFlex, [{
    key: "componentDidMount",
    value: function componentDidMount() {
      var _this2 = this;

      var model = new _model_admin_ChartFelxModel__WEBPACK_IMPORTED_MODULE_5__.default();
      model.getLabAccounts().then(function (res) {
        if (res) {
          _this2.setState({
            account_options: res
          });
        }
      });
    }
  }, {
    key: "getTimeRange",
    value: function getTimeRange() {
      var stopTime = Number(this.state.startTime) + Number(this.state.timeLeng) * 86400;
      return {
        startTime: Number(this.state.startTime),
        stopTime: stopTime
      };
    }
  }, {
    key: "getAccount",
    value: function getAccount() {
      return this.state.account;
    }
  }, {
    key: "render",
    value: function render() {
      var _this3 = this;

      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
        children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
          className: "box_flex",
          children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_4__.default, {
            className: "input",
            DateFormat: 'DD/MM/YYYY',
            type: "date",
            Direct: true,
            value: this.state.startTime,
            placeholder: "Start Time",
            OnChange: function OnChange(val) {
              val = Number(val);
              localStorage.setItem(_this3.storageStartTime, val);

              _this3.setState({
                startTime: val
              });
            }
          }), "\xA0", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_4__.default, {
            style: {
              width: 50
            },
            className: "input",
            type: "number",
            Direct: true,
            value: this.state.timeLeng,
            placeholder: "Days",
            OnChange: function OnChange(val) {
              val = Number(val);
              localStorage.setItem(_this3.storageTimeLength, val);

              _this3.setState({
                timeLeng: val
              });
            }
          }), "\xA0", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_Input_v2_Input__WEBPACK_IMPORTED_MODULE_4__.default, {
            className: "input",
            type: "select",
            Direct: true,
            value: Number(this.state.account),
            OnChange: function OnChange(val) {
              localStorage.setItem(_this3.storageAccountKey, val);

              _this3.setState({
                account: val
              });
            },
            Options: this.state.account_options
          }), "\xA0", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            className: "button btn btn-sm btn-info",
            onClick: function onClick() {
              _this3.chartPrice.updateAllData();

              _this3.chartFlex1.updateAllData();

              _this3.chartFlex2.updateAllData();
            },
            children: "Apply"
          })]
        }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_admin_ChartFlex_ChartFlexItem__WEBPACK_IMPORTED_MODULE_2__.default, {
          ref: function ref(c) {
            return _this3.chartPrice = c;
          },
          id: "flex_chart_00",
          sync: this.chartSycn,
          parent: this,
          isPosition: true
        }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_admin_ChartFlex_ChartFlexItem__WEBPACK_IMPORTED_MODULE_2__.default, {
          ref: function ref(c) {
            return _this3.chartFlex1 = c;
          },
          id: "flex_chart_01",
          sync: this.chartSycn,
          parent: this
        }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_admin_ChartFlex_ChartFlexItem__WEBPACK_IMPORTED_MODULE_2__.default, {
          ref: function ref(c) {
            return _this3.chartFlex2 = c;
          },
          id: "flex_chart_02",
          sync: this.chartSycn,
          parent: this
        })]
      });
    }
  }]);

  return ChartFlex;
}(react__WEBPACK_IMPORTED_MODULE_1__.Component);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (ChartFlex);

/***/ })

}]);