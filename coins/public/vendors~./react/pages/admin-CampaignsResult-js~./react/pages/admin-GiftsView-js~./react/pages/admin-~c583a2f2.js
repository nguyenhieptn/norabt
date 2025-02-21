(window["webpackJsonp"] = window["webpackJsonp"] || []).push([["vendors~./react/pages/admin-CampaignsResult-js~./react/pages/admin-GiftsView-js~./react/pages/admin-~c583a2f2"],{

/***/ "./node_modules/classnames/index.js":
/*!******************************************!*\
  !*** ./node_modules/classnames/index.js ***!
  \******************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/*!
  Copyright (c) 2017 Jed Watson.
  Licensed under the MIT License (MIT), see
  http://jedwatson.github.io/classnames
*/
/* global define */

(function () {
	'use strict';

	var hasOwn = {}.hasOwnProperty;

	function classNames () {
		var classes = [];

		for (var i = 0; i < arguments.length; i++) {
			var arg = arguments[i];
			if (!arg) continue;

			var argType = typeof arg;

			if (argType === 'string' || argType === 'number') {
				classes.push(arg);
			} else if (Array.isArray(arg) && arg.length) {
				var inner = classNames.apply(null, arg);
				if (inner) {
					classes.push(inner);
				}
			} else if (argType === 'object') {
				for (var key in arg) {
					if (hasOwn.call(arg, key) && arg[key]) {
						classes.push(key);
					}
				}
			}
		}

		return classes.join(' ');
	}

	if ( true && module.exports) {
		classNames.default = classNames;
		module.exports = classNames;
	} else if (true) {
		// register as 'classnames', consistent with npm package name
		!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = (function () {
			return classNames;
		}).apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__),
				__WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	} else {}
}());


/***/ }),

/***/ "./node_modules/primereact/checkbox.js":
/*!*********************************************!*\
  !*** ./node_modules/primereact/checkbox.js ***!
  \*********************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";


module.exports = __webpack_require__(/*! ./components/checkbox/Checkbox */ "./node_modules/primereact/components/checkbox/Checkbox.js");

/***/ }),

/***/ "./node_modules/primereact/components/checkbox/Checkbox.js":
/*!*****************************************************************!*\
  !*** ./node_modules/primereact/components/checkbox/Checkbox.js ***!
  \*****************************************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";


Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.Checkbox = void 0;

var _react = _interopRequireWildcard(__webpack_require__(/*! react */ "./node_modules/react/index.js"));

var _propTypes = _interopRequireDefault(__webpack_require__(/*! prop-types */ "./node_modules/prop-types/index.js"));

var _classnames = _interopRequireDefault(__webpack_require__(/*! classnames */ "./node_modules/classnames/index.js"));

var _Tooltip = _interopRequireDefault(__webpack_require__(/*! ../tooltip/Tooltip */ "./node_modules/primereact/components/tooltip/Tooltip.js"));

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _getRequireWildcardCache() { if (typeof WeakMap !== "function") return null; var cache = new WeakMap(); _getRequireWildcardCache = function _getRequireWildcardCache() { return cache; }; return cache; }

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } var cache = _getRequireWildcardCache(); if (cache && cache.has(obj)) { return cache.get(obj); } var newObj = {}; if (obj != null) { var hasPropertyDescriptor = Object.defineProperty && Object.getOwnPropertyDescriptor; for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) { var desc = hasPropertyDescriptor ? Object.getOwnPropertyDescriptor(obj, key) : null; if (desc && (desc.get || desc.set)) { Object.defineProperty(newObj, key, desc); } else { newObj[key] = obj[key]; } } } } newObj.default = obj; if (cache) { cache.set(obj, newObj); } return newObj; }

function _typeof(obj) { if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _possibleConstructorReturn(self, call) { if (call && (_typeof(call) === "object" || typeof call === "function")) { return call; } return _assertThisInitialized(self); }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

var Checkbox =
/*#__PURE__*/
function (_Component) {
  _inherits(Checkbox, _Component);

  function Checkbox(props) {
    var _this;

    _classCallCheck(this, Checkbox);

    _this = _possibleConstructorReturn(this, _getPrototypeOf(Checkbox).call(this, props));
    _this.state = {};
    _this.onClick = _this.onClick.bind(_assertThisInitialized(_this));
    _this.onFocus = _this.onFocus.bind(_assertThisInitialized(_this));
    _this.onBlur = _this.onBlur.bind(_assertThisInitialized(_this));
    _this.onKeyDown = _this.onKeyDown.bind(_assertThisInitialized(_this));
    return _this;
  }

  _createClass(Checkbox, [{
    key: "onClick",
    value: function onClick(e) {
      if (!this.props.disabled && !this.props.readOnly && this.props.onChange) {
        this.props.onChange({
          originalEvent: e,
          value: this.props.value,
          checked: !this.props.checked,
          stopPropagation: function stopPropagation() {},
          preventDefault: function preventDefault() {},
          target: {
            type: 'checkbox',
            name: this.props.name,
            id: this.props.id,
            value: this.props.value,
            checked: !this.props.checked
          }
        });
        this.input.checked = !this.props.checked;
        this.input.focus();
        e.preventDefault();
      }
    }
  }, {
    key: "componentDidMount",
    value: function componentDidMount() {
      if (this.props.tooltip) {
        this.renderTooltip();
      }
    }
  }, {
    key: "componentWillUnmount",
    value: function componentWillUnmount() {
      if (this.tooltip) {
        this.tooltip.destroy();
        this.tooltip = null;
      }
    }
  }, {
    key: "componentDidUpdate",
    value: function componentDidUpdate(prevProps) {
      this.input.checked = this.props.checked;

      if (prevProps.tooltip !== this.props.tooltip) {
        if (this.tooltip) this.tooltip.updateContent(this.props.tooltip);else this.renderTooltip();
      }
    }
  }, {
    key: "onFocus",
    value: function onFocus() {
      this.setState({
        focused: true
      });
    }
  }, {
    key: "onBlur",
    value: function onBlur() {
      this.setState({
        focused: false
      });
    }
  }, {
    key: "onKeyDown",
    value: function onKeyDown(event) {
      if (event.key === 'Enter') {
        this.onClick(event);
        event.preventDefault();
      }
    }
  }, {
    key: "renderTooltip",
    value: function renderTooltip() {
      this.tooltip = new _Tooltip.default({
        target: this.element,
        content: this.props.tooltip,
        options: this.props.tooltipOptions
      });
    }
  }, {
    key: "render",
    value: function render() {
      var _this2 = this;

      var containerClass = (0, _classnames.default)('p-checkbox p-component', this.props.className);
      var boxClass = (0, _classnames.default)('p-checkbox-box p-component', {
        'p-highlight': this.props.checked,
        'p-disabled': this.props.disabled,
        'p-focus': this.state.focused
      });
      var iconClass = (0, _classnames.default)('p-checkbox-icon p-c', {
        'pi pi-check': this.props.checked
      });
      return _react.default.createElement("div", {
        ref: function ref(el) {
          return _this2.element = el;
        },
        id: this.props.id,
        className: containerClass,
        style: this.props.style,
        onClick: this.onClick,
        onContextMenu: this.props.onContextMenu,
        onMouseDown: this.props.onMouseDown
      }, _react.default.createElement("div", {
        className: "p-hidden-accessible"
      }, _react.default.createElement("input", {
        type: "checkbox",
        "aria-labelledby": this.props.ariaLabelledBy,
        ref: function ref(el) {
          return _this2.input = el;
        },
        id: this.props.inputId,
        name: this.props.name,
        defaultChecked: this.props.checked,
        onKeyDown: this.onKeyDown,
        onFocus: this.onFocus,
        onBlur: this.onBlur,
        disabled: this.props.disabled,
        readOnly: this.props.readOnly,
        required: this.props.required
      })), _react.default.createElement("div", {
        className: boxClass,
        ref: function ref(el) {
          return _this2.box = el;
        },
        role: "checkbox",
        "aria-checked": this.props.checked
      }, _react.default.createElement("span", {
        className: iconClass
      })));
    }
  }]);

  return Checkbox;
}(_react.Component);

exports.Checkbox = Checkbox;

_defineProperty(Checkbox, "defaultProps", {
  id: null,
  inputId: null,
  value: null,
  name: null,
  checked: false,
  style: null,
  className: null,
  disabled: false,
  required: false,
  readOnly: false,
  tooltip: null,
  tooltipOptions: null,
  ariaLabelledBy: null,
  onChange: null,
  onMouseDown: null,
  onContextMenu: null
});

_defineProperty(Checkbox, "propTypes", {
  id: _propTypes.default.string,
  inputId: _propTypes.default.string,
  value: _propTypes.default.any,
  name: _propTypes.default.string,
  checked: _propTypes.default.bool,
  style: _propTypes.default.object,
  className: _propTypes.default.string,
  disabled: _propTypes.default.bool,
  required: _propTypes.default.bool,
  readOnly: _propTypes.default.bool,
  tooltip: _propTypes.default.string,
  tooltipOptions: _propTypes.default.object,
  ariaLabelledBy: _propTypes.default.string,
  onChange: _propTypes.default.func,
  onMouseDown: _propTypes.default.func,
  onContextMenu: _propTypes.default.func
});

/***/ }),

/***/ "./node_modules/primereact/components/tooltip/Tooltip.js":
/*!***************************************************************!*\
  !*** ./node_modules/primereact/components/tooltip/Tooltip.js ***!
  \***************************************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";


Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;

var _DomHandler = _interopRequireDefault(__webpack_require__(/*! ../utils/DomHandler */ "./node_modules/primereact/components/utils/DomHandler.js"));

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

var Tooltip =
/*#__PURE__*/
function () {
  function Tooltip(props) {
    _classCallCheck(this, Tooltip);

    this.target = props.target;
    this.targetContainer = props.targetContainer;
    this.content = props.content;
    this.options = props.options || {};
    this.options.event = this.options.event || 'hover';
    this.options.position = this.options.position || 'right';
    this.bindEvents();
  }

  _createClass(Tooltip, [{
    key: "bindEvents",
    value: function bindEvents() {
      if (this.options.event === 'hover') {
        this.mouseEnterListener = this.onMouseEnter.bind(this);
        this.mouseLeaveListener = this.onMouseLeave.bind(this);
        this.clickListener = this.onClick.bind(this);
        this.target.addEventListener('mouseenter', this.mouseEnterListener);
        this.target.addEventListener('mouseleave', this.mouseLeaveListener);
        this.target.addEventListener('click', this.clickListener);
      } else if (this.options.event === 'focus') {
        this.focusListener = this.onFocus.bind(this);
        this.blurListener = this.onBlur.bind(this);
        this.target.addEventListener('focus', this.focusListener);
        this.target.addEventListener('blur', this.blurListener);
      }
    }
  }, {
    key: "unbindEvents",
    value: function unbindEvents() {
      if (this.options.event === 'hover') {
        this.target.removeEventListener('mouseenter', this.mouseEnterListener);
        this.target.removeEventListener('mouseleave', this.mouseLeaveListener);
        this.target.removeEventListener('click', this.clickListener);
      } else if (this.options.event === 'focus') {
        this.target.removeEventListener('focus', this.focusListener);
        this.target.removeEventListener('blur', this.blurListener);
      }

      this.unbindDocumentResizeListener();
    }
  }, {
    key: "onMouseEnter",
    value: function onMouseEnter() {
      if (!this.container && !this.showTimeout) {
        this.activate();
      }
    }
  }, {
    key: "onMouseLeave",
    value: function onMouseLeave() {
      this.deactivate();
    }
  }, {
    key: "onFocus",
    value: function onFocus() {
      this.activate();
    }
  }, {
    key: "onBlur",
    value: function onBlur() {
      this.deactivate();
    }
  }, {
    key: "onClick",
    value: function onClick() {
      this.deactivate();
    }
  }, {
    key: "activate",
    value: function activate() {
      var _this = this;

      this.clearHideTimeout();
      if (this.options.showDelay) this.showTimeout = setTimeout(function () {
        _this.show();
      }, this.options.showDelay);else this.show();
    }
  }, {
    key: "deactivate",
    value: function deactivate() {
      var _this2 = this;

      this.clearShowTimeout();
      if (this.options.hideDelay) this.hideTimeout = setTimeout(function () {
        _this2.hide();
      }, this.options.hideDelay);else this.hide();
    }
  }, {
    key: "clearShowTimeout",
    value: function clearShowTimeout() {
      if (this.showTimeout) {
        clearTimeout(this.showTimeout);
        this.showTimeout = null;
      }
    }
  }, {
    key: "clearHideTimeout",
    value: function clearHideTimeout() {
      if (this.hideTimeout) {
        clearTimeout(this.hideTimeout);
        this.hideTimeout = null;
      }
    }
  }, {
    key: "clearTimeouts",
    value: function clearTimeouts() {
      this.clearShowTimeout();
      this.clearHideTimeout();
    }
  }, {
    key: "updateContent",
    value: function updateContent(content) {
      this.content = content;
    }
  }, {
    key: "show",
    value: function show() {
      if (!this.content) {
        return;
      }

      this.create();
      this.align();

      _DomHandler.default.fadeIn(this.container, 250);

      this.container.style.zIndex = ++_DomHandler.default.zindex;
      this.bindDocumentResizeListener();
    }
  }, {
    key: "hide",
    value: function hide() {
      this.remove();
    }
  }, {
    key: "create",
    value: function create() {
      this.container = document.createElement('div');
      var tooltipArrow = document.createElement('div');
      tooltipArrow.className = 'p-tooltip-arrow';
      this.container.appendChild(tooltipArrow);
      this.tooltipText = document.createElement('div');
      this.tooltipText.className = 'p-tooltip-text'; //todo: JSX support

      this.tooltipText.innerHTML = this.content;
      this.container.appendChild(this.tooltipText);
      document.body.appendChild(this.container);
      this.container.style.display = 'inline-block';
    }
  }, {
    key: "remove",
    value: function remove() {
      if (this.container && this.container.parentElement) {
        document.body.removeChild(this.container);
      }

      this.unbindDocumentResizeListener();
      this.clearTimeouts();
      this.container = null;
    }
  }, {
    key: "align",
    value: function align() {
      switch (this.options.position) {
        case 'top':
          this.alignTop();

          if (this.isOutOfBounds()) {
            this.alignBottom();
          }

          break;

        case 'bottom':
          this.alignBottom();

          if (this.isOutOfBounds()) {
            this.alignTop();
          }

          break;

        case 'left':
          this.alignLeft();

          if (this.isOutOfBounds()) {
            this.alignRight();

            if (this.isOutOfBounds()) {
              this.alignTop();

              if (this.isOutOfBounds()) {
                this.alignBottom();
              }
            }
          }

          break;

        case 'right':
          this.alignRight();

          if (this.isOutOfBounds()) {
            this.alignLeft();

            if (this.isOutOfBounds()) {
              this.alignTop();

              if (this.isOutOfBounds()) {
                this.alignBottom();
              }
            }
          }

          break;

        default:
          throw new Error('Invalid position:' + this.options.position);
      }
    }
  }, {
    key: "getHostOffset",
    value: function getHostOffset() {
      var target = this.targetContainer || this.target;
      var offset = target.getBoundingClientRect();

      var targetLeft = offset.left + _DomHandler.default.getWindowScrollLeft();

      var targetTop = offset.top + _DomHandler.default.getWindowScrollTop();

      return {
        left: targetLeft,
        top: targetTop
      };
    }
  }, {
    key: "alignRight",
    value: function alignRight() {
      this.preAlign('right');
      var target = this.targetContainer || this.target;
      var hostOffset = this.getHostOffset();

      var left = hostOffset.left + _DomHandler.default.getOuterWidth(target);

      var top = hostOffset.top + (_DomHandler.default.getOuterHeight(target) - _DomHandler.default.getOuterHeight(this.container)) / 2;
      this.container.style.left = left + 'px';
      this.container.style.top = top + 'px';
    }
  }, {
    key: "alignLeft",
    value: function alignLeft() {
      this.preAlign('left');
      var target = this.targetContainer || this.target;
      var hostOffset = this.getHostOffset();

      var left = hostOffset.left - _DomHandler.default.getOuterWidth(this.container);

      var top = hostOffset.top + (_DomHandler.default.getOuterHeight(target) - _DomHandler.default.getOuterHeight(this.container)) / 2;
      this.container.style.left = left + 'px';
      this.container.style.top = top + 'px';
    }
  }, {
    key: "alignTop",
    value: function alignTop() {
      this.preAlign('top');
      var target = this.targetContainer || this.target;
      var hostOffset = this.getHostOffset();
      var left = hostOffset.left + (_DomHandler.default.getOuterWidth(target) - _DomHandler.default.getOuterWidth(this.container)) / 2;

      var top = hostOffset.top - _DomHandler.default.getOuterHeight(this.container);

      this.container.style.left = left + 'px';
      this.container.style.top = top + 'px';
    }
  }, {
    key: "alignBottom",
    value: function alignBottom() {
      this.preAlign('bottom');
      var target = this.targetContainer || this.target;
      var hostOffset = this.getHostOffset();
      var left = hostOffset.left + (_DomHandler.default.getOuterWidth(target) - _DomHandler.default.getOuterWidth(this.container)) / 2;

      var top = hostOffset.top + _DomHandler.default.getOuterHeight(target);

      this.container.style.left = left + 'px';
      this.container.style.top = top + 'px';
    }
  }, {
    key: "preAlign",
    value: function preAlign(position) {
      this.container.style.left = -999 + 'px';
      this.container.style.top = -999 + 'px';
      var defaultClassName = 'p-tooltip p-component p-tooltip-' + position;
      this.container.className = this.options.className ? defaultClassName + ' ' + this.options.className : defaultClassName;
    }
  }, {
    key: "isOutOfBounds",
    value: function isOutOfBounds() {
      var offset = this.container.getBoundingClientRect();
      var targetTop = offset.top;
      var targetLeft = offset.left;

      var width = _DomHandler.default.getOuterWidth(this.container);

      var height = _DomHandler.default.getOuterHeight(this.container);

      var viewport = _DomHandler.default.getViewport();

      return targetLeft + width > viewport.width || targetLeft < 0 || targetTop < 0 || targetTop + height > viewport.height;
    }
  }, {
    key: "bindDocumentResizeListener",
    value: function bindDocumentResizeListener() {
      this.resizeListener = this.onWindowResize.bind(this);
      window.addEventListener('resize', this.resizeListener);
    }
  }, {
    key: "unbindDocumentResizeListener",
    value: function unbindDocumentResizeListener() {
      if (this.resizeListener) {
        window.removeEventListener('resize', this.resizeListener);
        this.resizeListener = null;
      }
    }
  }, {
    key: "onWindowResize",
    value: function onWindowResize() {
      this.hide();
    }
  }, {
    key: "destroy",
    value: function destroy() {
      this.unbindEvents();
      this.remove();
      this.target = null;
      this.targetContainer = null;
    }
  }]);

  return Tooltip;
}();

exports.default = Tooltip;

/***/ }),

/***/ "./node_modules/primereact/components/utils/DomHandler.js":
/*!****************************************************************!*\
  !*** ./node_modules/primereact/components/utils/DomHandler.js ***!
  \****************************************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";


Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

var DomHandler =
/*#__PURE__*/
function () {
  function DomHandler() {
    _classCallCheck(this, DomHandler);
  }

  _createClass(DomHandler, null, [{
    key: "innerWidth",
    value: function innerWidth(el) {
      if (el) {
        var width = el.offsetWidth;
        var style = getComputedStyle(el);
        width += parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
        return width;
      }

      return 0;
    }
  }, {
    key: "width",
    value: function width(el) {
      if (el) {
        var width = el.offsetWidth;
        var style = getComputedStyle(el);
        width -= parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
        return width;
      }

      return 0;
    }
  }, {
    key: "getWindowScrollTop",
    value: function getWindowScrollTop() {
      var doc = document.documentElement;
      return (window.pageYOffset || doc.scrollTop) - (doc.clientTop || 0);
    }
  }, {
    key: "getWindowScrollLeft",
    value: function getWindowScrollLeft() {
      var doc = document.documentElement;
      return (window.pageXOffset || doc.scrollLeft) - (doc.clientLeft || 0);
    }
  }, {
    key: "getOuterWidth",
    value: function getOuterWidth(el, margin) {
      if (el) {
        var width = el.offsetWidth;

        if (margin) {
          var style = getComputedStyle(el);
          width += parseFloat(style.marginLeft) + parseFloat(style.marginRight);
        }

        return width;
      }

      return 0;
    }
  }, {
    key: "getOuterHeight",
    value: function getOuterHeight(el, margin) {
      if (el) {
        var height = el.offsetHeight;

        if (margin) {
          var style = getComputedStyle(el);
          height += parseFloat(style.marginTop) + parseFloat(style.marginBottom);
        }

        return height;
      }

      return 0;
    }
  }, {
    key: "getClientHeight",
    value: function getClientHeight(el, margin) {
      if (el) {
        var height = el.clientHeight;

        if (margin) {
          var style = getComputedStyle(el);
          height += parseFloat(style.marginTop) + parseFloat(style.marginBottom);
        }

        return height;
      }

      return 0;
    }
  }, {
    key: "getViewport",
    value: function getViewport() {
      var win = window,
          d = document,
          e = d.documentElement,
          g = d.getElementsByTagName('body')[0],
          w = win.innerWidth || e.clientWidth || g.clientWidth,
          h = win.innerHeight || e.clientHeight || g.clientHeight;
      return {
        width: w,
        height: h
      };
    }
  }, {
    key: "getOffset",
    value: function getOffset(el) {
      if (el) {
        var rect = el.getBoundingClientRect();
        return {
          top: rect.top + document.body.scrollTop,
          left: rect.left + document.body.scrollLeft
        };
      }

      return {
        top: 'auto',
        left: 'auto'
      };
    }
  }, {
    key: "generateZIndex",
    value: function generateZIndex() {
      this.zindex = this.zindex || 999;
      return ++this.zindex;
    }
  }, {
    key: "getCurrentZIndex",
    value: function getCurrentZIndex() {
      return this.zindex;
    }
  }, {
    key: "index",
    value: function index(element) {
      if (element) {
        var children = element.parentNode.childNodes;
        var num = 0;

        for (var i = 0; i < children.length; i++) {
          if (children[i] === element) return num;
          if (children[i].nodeType === 1) num++;
        }
      }

      return -1;
    }
  }, {
    key: "addMultipleClasses",
    value: function addMultipleClasses(element, className) {
      if (element) {
        if (element.classList) {
          var styles = className.split(' ');

          for (var i = 0; i < styles.length; i++) {
            element.classList.add(styles[i]);
          }
        } else {
          var _styles = className.split(' ');

          for (var _i = 0; _i < _styles.length; _i++) {
            element.className += ' ' + _styles[_i];
          }
        }
      }
    }
  }, {
    key: "addClass",
    value: function addClass(element, className) {
      if (element) {
        if (element.classList) element.classList.add(className);else element.className += ' ' + className;
      }
    }
  }, {
    key: "removeClass",
    value: function removeClass(element, className) {
      if (element) {
        if (element.classList) element.classList.remove(className);else element.className = element.className.replace(new RegExp('(^|\\b)' + className.split(' ').join('|') + '(\\b|$)', 'gi'), ' ');
      }
    }
  }, {
    key: "hasClass",
    value: function hasClass(element, className) {
      if (element) {
        if (element.classList) return element.classList.contains(className);else return new RegExp('(^| )' + className + '( |$)', 'gi').test(element.className);
      }
    }
  }, {
    key: "find",
    value: function find(element, selector) {
      return element ? Array.from(element.querySelectorAll(selector)) : [];
    }
  }, {
    key: "findSingle",
    value: function findSingle(element, selector) {
      if (element) {
        return element.querySelector(selector);
      }

      return null;
    }
  }, {
    key: "getHeight",
    value: function getHeight(el) {
      if (el) {
        var height = el.offsetHeight;
        var style = getComputedStyle(el);
        height -= parseFloat(style.paddingTop) + parseFloat(style.paddingBottom) + parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
        return height;
      }

      return 0;
    }
  }, {
    key: "getWidth",
    value: function getWidth(el) {
      if (el) {
        var width = el.offsetWidth;
        var style = getComputedStyle(el);
        width -= parseFloat(style.paddingLeft) + parseFloat(style.paddingRight) + parseFloat(style.borderLeftWidth) + parseFloat(style.borderRightWidth);
        return width;
      }

      return 0;
    }
  }, {
    key: "absolutePosition",
    value: function absolutePosition(element, target) {
      if (element) {
        var elementDimensions = element.offsetParent ? {
          width: element.offsetWidth,
          height: element.offsetHeight
        } : this.getHiddenElementDimensions(element);
        var elementOuterHeight = elementDimensions.height;
        var elementOuterWidth = elementDimensions.width;
        var targetOuterHeight = target.offsetHeight;
        var targetOuterWidth = target.offsetWidth;
        var targetOffset = target.getBoundingClientRect();
        var windowScrollTop = this.getWindowScrollTop();
        var windowScrollLeft = this.getWindowScrollLeft();
        var viewport = this.getViewport();
        var top, left;

        if (targetOffset.top + targetOuterHeight + elementOuterHeight > viewport.height) {
          top = targetOffset.top + windowScrollTop - elementOuterHeight;

          if (top < 0) {
            top = windowScrollTop;
          }
        } else {
          top = targetOuterHeight + targetOffset.top + windowScrollTop;
        }

        if (targetOffset.left + targetOuterWidth + elementOuterWidth > viewport.width) left = Math.max(0, targetOffset.left + windowScrollLeft + targetOuterWidth - elementOuterWidth);else left = targetOffset.left + windowScrollLeft;
        element.style.top = top + 'px';
        element.style.left = left + 'px';
      }
    }
  }, {
    key: "relativePosition",
    value: function relativePosition(element, target) {
      if (element) {
        var elementDimensions = element.offsetParent ? {
          width: element.offsetWidth,
          height: element.offsetHeight
        } : this.getHiddenElementDimensions(element);
        var targetHeight = target.offsetHeight;
        var targetOffset = target.getBoundingClientRect();
        var viewport = this.getViewport();
        var top, left;

        if (targetOffset.top + targetHeight + elementDimensions.height > viewport.height) {
          top = -1 * elementDimensions.height;

          if (targetOffset.top + top < 0) {
            top = -1 * targetOffset.top;
          }
        } else {
          top = targetHeight;
        }

        if (elementDimensions.width > viewport.width) {
          // element wider then viewport and cannot fit on screen (align at left side of viewport)
          left = targetOffset.left * -1;
        } else if (targetOffset.left + elementDimensions.width > viewport.width) {
          // element wider then viewport but can be fit on screen (align at right side of viewport)
          left = (targetOffset.left + elementDimensions.width - viewport.width) * -1;
        } else {
          // element fits on screen (align with target)
          left = 0;
        }

        element.style.top = top + 'px';
        element.style.left = left + 'px';
      }
    }
  }, {
    key: "getHiddenElementOuterHeight",
    value: function getHiddenElementOuterHeight(element) {
      if (element) {
        element.style.visibility = 'hidden';
        element.style.display = 'block';
        var elementHeight = element.offsetHeight;
        element.style.display = 'none';
        element.style.visibility = 'visible';
        return elementHeight;
      }

      return 0;
    }
  }, {
    key: "getHiddenElementOuterWidth",
    value: function getHiddenElementOuterWidth(element) {
      if (element) {
        element.style.visibility = 'hidden';
        element.style.display = 'block';
        var elementWidth = element.offsetWidth;
        element.style.display = 'none';
        element.style.visibility = 'visible';
        return elementWidth;
      }

      return 0;
    }
  }, {
    key: "getHiddenElementDimensions",
    value: function getHiddenElementDimensions(element) {
      var dimensions = {};

      if (element) {
        element.style.visibility = 'hidden';
        element.style.display = 'block';
        dimensions.width = element.offsetWidth;
        dimensions.height = element.offsetHeight;
        element.style.display = 'none';
        element.style.visibility = 'visible';
      }

      return dimensions;
    }
  }, {
    key: "fadeIn",
    value: function fadeIn(element, duration) {
      if (element) {
        element.style.opacity = 0;
        var last = +new Date();
        var opacity = 0;

        var tick = function tick() {
          opacity = +element.style.opacity + (new Date().getTime() - last) / duration;
          element.style.opacity = opacity;
          last = +new Date();

          if (+opacity < 1) {
            window.requestAnimationFrame && requestAnimationFrame(tick) || setTimeout(tick, 16);
          }
        };

        tick();
      }
    }
  }, {
    key: "fadeOut",
    value: function fadeOut(element, ms) {
      if (element) {
        var opacity = 1,
            interval = 50,
            duration = ms,
            gap = interval / duration;
        var fading = setInterval(function () {
          opacity -= gap;

          if (opacity <= 0) {
            opacity = 0;
            clearInterval(fading);
          }

          element.style.opacity = opacity;
        }, interval);
      }
    }
  }, {
    key: "getUserAgent",
    value: function getUserAgent() {
      return navigator.userAgent;
    }
  }, {
    key: "isIOS",
    value: function isIOS() {
      return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window['MSStream'];
    }
  }, {
    key: "isAndroid",
    value: function isAndroid() {
      return /(android)/i.test(navigator.userAgent);
    }
  }, {
    key: "appendChild",
    value: function appendChild(element, target) {
      if (this.isElement(target)) target.appendChild(element);else if (target.el && target.el.nativeElement) target.el.nativeElement.appendChild(element);else throw new Error('Cannot append ' + target + ' to ' + element);
    }
  }, {
    key: "scrollInView",
    value: function scrollInView(container, item) {
      var borderTopValue = getComputedStyle(container).getPropertyValue('borderTopWidth');
      var borderTop = borderTopValue ? parseFloat(borderTopValue) : 0;
      var paddingTopValue = getComputedStyle(container).getPropertyValue('paddingTop');
      var paddingTop = paddingTopValue ? parseFloat(paddingTopValue) : 0;
      var containerRect = container.getBoundingClientRect();
      var itemRect = item.getBoundingClientRect();
      var offset = itemRect.top + document.body.scrollTop - (containerRect.top + document.body.scrollTop) - borderTop - paddingTop;
      var scroll = container.scrollTop;
      var elementHeight = container.clientHeight;
      var itemHeight = this.getOuterHeight(item);

      if (offset < 0) {
        container.scrollTop = scroll + offset;
      } else if (offset + itemHeight > elementHeight) {
        container.scrollTop = scroll + offset - elementHeight + itemHeight;
      }
    }
  }, {
    key: "clearSelection",
    value: function clearSelection() {
      if (window.getSelection) {
        if (window.getSelection().empty) {
          window.getSelection().empty();
        } else if (window.getSelection().removeAllRanges && window.getSelection().rangeCount > 0 && window.getSelection().getRangeAt(0).getClientRects().length > 0) {
          window.getSelection().removeAllRanges();
        }
      } else if (document['selection'] && document['selection'].empty) {
        try {
          document['selection'].empty();
        } catch (error) {//ignore IE bug
        }
      }
    }
  }, {
    key: "calculateScrollbarWidth",
    value: function calculateScrollbarWidth(el) {
      if (el) {
        var style = getComputedStyle(el);
        return el.offsetWidth - el.clientWidth - parseFloat(style.borderLeftWidth) - parseFloat(style.borderRightWidth);
      } else {
        if (this.calculatedScrollbarWidth != null) return this.calculatedScrollbarWidth;
        var scrollDiv = document.createElement("div");
        scrollDiv.className = "p-scrollbar-measure";
        document.body.appendChild(scrollDiv);
        var scrollbarWidth = scrollDiv.offsetWidth - scrollDiv.clientWidth;
        document.body.removeChild(scrollDiv);
        this.calculatedScrollbarWidth = scrollbarWidth;
        return scrollbarWidth;
      }
    }
  }, {
    key: "getBrowser",
    value: function getBrowser() {
      if (!this.browser) {
        var matched = this.resolveUserAgent();
        this.browser = {};

        if (matched.browser) {
          this.browser[matched.browser] = true;
          this.browser['version'] = matched.version;
        }

        if (this.browser['chrome']) {
          this.browser['webkit'] = true;
        } else if (this.browser['webkit']) {
          this.browser['safari'] = true;
        }
      }

      return this.browser;
    }
  }, {
    key: "resolveUserAgent",
    value: function resolveUserAgent() {
      var ua = navigator.userAgent.toLowerCase();
      var match = /(chrome)[ ]([\w.]+)/.exec(ua) || /(webkit)[ ]([\w.]+)/.exec(ua) || /(opera)(?:.*version|)[ ]([\w.]+)/.exec(ua) || /(msie) ([\w.]+)/.exec(ua) || ua.indexOf("compatible") < 0 && /(mozilla)(?:.*? rv:([\w.]+)|)/.exec(ua) || [];
      return {
        browser: match[1] || "",
        version: match[2] || "0"
      };
    }
  }, {
    key: "isVisible",
    value: function isVisible(element) {
      return element && element.offsetParent != null;
    }
  }, {
    key: "getFocusableElements",
    value: function getFocusableElements(element) {
      var focusableElements = DomHandler.find(element, "button:not([tabindex = \"-1\"]):not([disabled]):not([style*=\"display:none\"]):not([hidden]), \n                [href][clientHeight][clientWidth]:not([tabindex = \"-1\"]):not([disabled]):not([style*=\"display:none\"]):not([hidden]), \n                input:not([tabindex = \"-1\"]):not([disabled]):not([style*=\"display:none\"]):not([hidden]), select:not([tabindex = \"-1\"]):not([disabled]):not([style*=\"display:none\"]):not([hidden]), \n                textarea:not([tabindex = \"-1\"]):not([disabled]):not([style*=\"display:none\"]):not([hidden]), [tabIndex]:not([tabIndex = \"-1\"]):not([disabled]):not([style*=\"display:none\"]):not([hidden]), \n                [contenteditable]:not([tabIndex = \"-1\"]):not([disabled]):not([style*=\"display:none\"]):not([hidden])");
      var visibleFocusableElements = [];
      var _iteratorNormalCompletion = true;
      var _didIteratorError = false;
      var _iteratorError = undefined;

      try {
        for (var _iterator = focusableElements[Symbol.iterator](), _step; !(_iteratorNormalCompletion = (_step = _iterator.next()).done); _iteratorNormalCompletion = true) {
          var focusableElement = _step.value;
          if (getComputedStyle(focusableElement).display !== "none" && getComputedStyle(focusableElement).visibility !== "hidden") visibleFocusableElements.push(focusableElement);
        }
      } catch (err) {
        _didIteratorError = true;
        _iteratorError = err;
      } finally {
        try {
          if (!_iteratorNormalCompletion && _iterator.return != null) {
            _iterator.return();
          }
        } finally {
          if (_didIteratorError) {
            throw _iteratorError;
          }
        }
      }

      return visibleFocusableElements;
    }
  }]);

  return DomHandler;
}();

exports.default = DomHandler;

/***/ })

}]);